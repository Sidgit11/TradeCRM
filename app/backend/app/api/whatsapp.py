"""WhatsApp API — onboarding, templates, messaging, 24hr window."""
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.tenant import Tenant
from app.models.contact import Contact
from app.integrations.gupshup import gupshup_service
from app.integrations.gupshup_direct import gupshup_direct

logger = get_logger("api.whatsapp")
router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


# --- Schemas ---

class TemplateCreateRequest(BaseModel):
    name: str
    category: str = "MARKETING"
    language: str = "en"
    content: str  # Template body with {{1}}, {{2}} placeholders
    example: str  # Sample values for review


class SendTemplateRequest(BaseModel):
    contact_id: uuid.UUID
    template_id: str
    params: list = []


class SendSessionRequest(BaseModel):
    contact_id: uuid.UUID
    text: str


# --- Onboarding ---

@router.post("/onboarding/start")
async def start_whatsapp_onboarding(
    user: CurrentUser,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Start WhatsApp connection. Uses Direct API if Partner API isn't available."""
    from app.config import settings as s

    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()

    if tenant.whatsapp_status == "active":
        return {"status": "already_connected", "phone": tenant.whatsapp_phone}

    # Direct API mode — use own WABA number
    if gupshup_direct.is_configured:
        tenant.whatsapp_phone = s.GUPSHUP_WABA_NUMBER
        tenant.whatsapp_status = "active"
        tenant.whatsapp_connected_at = datetime.now(timezone.utc)
        tenant.gupshup_app_name = "tradecrm_direct"
        await db.commit()
        logger.info("whatsapp: direct mode connected | tenant=%s phone=%s", str(tenant_id)[:8], s.GUPSHUP_WABA_NUMBER)
        return {
            "status": "active",
            "phone": s.GUPSHUP_WABA_NUMBER,
            "mode": "direct",
            "message": "WhatsApp connected using your WABA number.",
        }

    # Partner API mode (multi-tenant)
    if gupshup_service.is_configured:
        try:
            if not tenant.gupshup_app_id:
                app_name = f"tradecrm_{str(tenant_id)[:8]}_{tenant.company_name[:20].replace(' ', '_').lower()}"
                result = await gupshup_service.create_app(app_name)
                tenant.gupshup_app_id = result["app_id"]
                tenant.gupshup_app_name = app_name
                tenant.whatsapp_status = "onboarding"
                await db.commit()

            callback_url = s.GUPSHUP_WEBHOOK_URL or f"{s.BACKEND_URL}/webhooks/gupshup"
            await gupshup_service.set_callback_url(tenant.gupshup_app_id, callback_url)
            embed_url = await gupshup_service.generate_embed_link(tenant.gupshup_app_id, user.email)

            return {"status": "onboarding", "app_id": tenant.gupshup_app_id, "embed_url": embed_url}
        except Exception as e:
            logger.error("whatsapp: partner onboarding failed | tenant=%s error=%s", str(tenant_id)[:8], str(e), exc_info=True)
            raise HTTPException(status_code=500, detail="WhatsApp setup failed. Please try again.")

    raise HTTPException(status_code=400, detail="WhatsApp not configured. Add Gupshup credentials to .env file.")


@router.post("/onboarding/complete")
async def complete_whatsapp_onboarding(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Called after customer completes Embedded Signup. Whitelists WABA and verifies."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()

    if not tenant.gupshup_app_id:
        raise HTTPException(status_code=400, detail="No Gupshup app found. Start onboarding first.")

    try:
        # Whitelist + verify
        await gupshup_service.whitelist_waba(tenant.gupshup_app_id)
        await gupshup_service.verify_and_attach_credit(tenant.gupshup_app_id)

        # Get app details (phone number etc)
        details = await gupshup_service.get_app_details(tenant.gupshup_app_id)
        phone = details.get("phoneNumber", details.get("phone", ""))

        tenant.whatsapp_phone = phone
        tenant.whatsapp_status = "active"
        tenant.whatsapp_connected_at = datetime.now(timezone.utc)

        # Get and cache app token
        app_token = await gupshup_service.get_app_token(tenant.gupshup_app_id)
        tenant.gupshup_app_token = app_token

        await db.commit()
        logger.info("whatsapp: onboarding complete | tenant=%s phone=%s", str(tenant_id)[:8], phone)
    except Exception as e:
        logger.error("whatsapp: onboarding complete failed | tenant=%s error=%s", str(tenant_id)[:8], str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="WhatsApp verification failed. Please try again.")

    return {"status": "active", "phone": phone, "app_id": tenant.gupshup_app_id}


@router.get("/status")
async def get_whatsapp_status(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get current WhatsApp connection status."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    return {
        "status": tenant.whatsapp_status or "not_connected",
        "phone": tenant.whatsapp_phone,
        "app_id": tenant.gupshup_app_id,
        "connected_at": tenant.whatsapp_connected_at.isoformat() if tenant.whatsapp_connected_at else None,
    }


@router.post("/disconnect")
async def disconnect_whatsapp(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Disconnect WhatsApp (soft — doesn't delete the Gupshup app)."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    tenant.whatsapp_status = "disconnected"
    tenant.gupshup_app_token = None
    await db.commit()
    logger.info("whatsapp: disconnected | tenant=%s", str(tenant_id)[:8])
    return {"status": "disconnected"}


# --- Templates (fetched from Gupshup) ---

GUPSHUP_TEMPLATE_API = "https://wamedia.smsgupshup.com/GatewayAPI/rest"


@router.get("/templates")
async def list_templates(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Fetch WhatsApp templates directly from Gupshup API."""
    import httpx as hx
    from app.config import settings as s
    import re

    if not s.GUPSHUP_HSM_USERID:
        return []

    all_templates = []
    offset = 0
    limit = 50

    async with hx.AsyncClient(timeout=30) as client:
        while True:
            r = await client.get(GUPSHUP_TEMPLATE_API, params={
                "method": "get_whatsapp_hsm",
                "userid": s.GUPSHUP_HSM_USERID,
                "password": s.GUPSHUP_HSM_PASSWORD,
                "limit": limit,
                "offset": offset,
                "fields": '["buttons"]',
            })

            if r.status_code != 200:
                logger.error("whatsapp: template fetch failed | status=%d", r.status_code)
                break

            data = r.json()
            templates = data.get("data", [])
            all_templates.extend(templates)

            total = data.get("meta", {}).get("total", 0)
            if offset + limit >= total or not templates:
                break
            offset += limit

    logger.info("whatsapp: fetched %d templates from Gupshup", len(all_templates))

    return [
        {
            "id": str(t.get("id", "")),
            "template_name": t.get("name", ""),
            "category": t.get("category", ""),
            "language": t.get("language", "en"),
            "content": t.get("body", ""),
            "type": t.get("type", "TEXT"),
            "status": t.get("status", ""),
            "quality_score": t.get("quality_score", ""),
            "buttons": t.get("buttons", []),
            "variables": re.findall(r'\{\{(\w+)\}\}', t.get("body", "")),
        }
        for t in all_templates
    ]


@router.post("/templates", status_code=201)
async def create_template(
    body: TemplateCreateRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Create a WhatsApp template locally. Copy template name and content from Gupshup Unify Dashboard."""
    from app.models.wa_template import WhatsAppTemplate
    import re

    # Extract variables from content ({{1}}, {{2}} or {{name}})
    variables = re.findall(r'\{\{(\w+)\}\}', body.content)

    template = WhatsAppTemplate(
        tenant_id=tenant_id,
        template_name=body.name,
        category=body.category,
        language=body.language,
        content=body.content,
        variables=variables,
        sample_values=body.example.split(",") if body.example else [],
        status="approved",  # User says it's approved in Gupshup
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info("whatsapp: template created locally | name=%s tenant=%s", body.name, str(tenant_id)[:8])
    return {"id": str(template.id), "template_name": template.template_name, "status": "approved"}


@router.delete("/templates/{template_id}", status_code=204)
async def delete_template(
    template_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Delete a locally managed template."""
    from app.models.wa_template import WhatsAppTemplate
    template = (await db.execute(
        select(WhatsAppTemplate).where(WhatsAppTemplate.id == template_id, WhatsAppTemplate.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if template:
        await db.delete(template)
        await db.commit()


# --- Messaging ---

@router.post("/send/template")
async def send_template(
    body: SendTemplateRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Send a template message to a contact."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    if tenant.whatsapp_status != "active":
        raise HTTPException(status_code=400, detail="WhatsApp not active")

    contact = (await db.execute(
        select(Contact).where(Contact.id == body.contact_id, Contact.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not contact or not contact.phone:
        raise HTTPException(status_code=400, detail="Contact not found or has no phone number")

    phone = contact.phone.replace("+", "").replace(" ", "")

    # Use direct API
    if gupshup_direct.is_configured:
        result = await gupshup_direct.send_hsm_message(
            destination=phone, template_name=body.template_id,
            namespace="", params=body.params,
        )
    else:
        result = await gupshup_service.send_template_message(
            app_id=tenant.gupshup_app_id or "", app_name=tenant.gupshup_app_name or "",
            source_phone=tenant.whatsapp_phone or "", destination_phone=phone,
            template_id=body.template_id, params=body.params,
        )

    logger.info("whatsapp: template sent | to=%s template=%s success=%s", phone, body.template_id, result.success)
    return {"success": result.success, "message_id": result.message_id, "error": result.error}


@router.post("/send/session")
async def send_session_message(
    body: SendSessionRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Send a free-form session message (only within 24hr window)."""
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one()
    if tenant.whatsapp_status != "active":
        raise HTTPException(status_code=400, detail="WhatsApp not active")

    contact = (await db.execute(
        select(Contact).where(Contact.id == body.contact_id, Contact.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not contact or not contact.phone:
        raise HTTPException(status_code=400, detail="Contact not found or has no phone number")

    window = await check_24hr_window(contact)
    if not window["is_open"]:
        raise HTTPException(status_code=400,
            detail=f"24-hour session window is closed. Use a template message instead.")

    phone = contact.phone.replace("+", "").replace(" ", "")

    if gupshup_direct.is_configured:
        result = await gupshup_direct.send_session_message(destination=phone, text=body.text)
    else:
        result = await gupshup_service.send_session_message(
            app_id=tenant.gupshup_app_id or "", app_name=tenant.gupshup_app_name or "",
            source_phone=tenant.whatsapp_phone or "", destination_phone=phone, text=body.text,
        )

    logger.info("whatsapp: session msg sent | to=%s success=%s", phone, result.success)
    return {"success": result.success, "message_id": result.message_id, "error": result.error}


# --- 24hr Window ---

@router.get("/window/{contact_id}")
async def get_window_status(
    contact_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Check if 24hr session window is open for a contact."""
    contact = (await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    return await check_24hr_window(contact)


async def check_24hr_window(contact: Contact) -> dict:
    """Check if session window is open for a contact."""
    if not contact.last_inbound_whatsapp_at:
        return {"is_open": False, "requires_template": True, "expires_at": None, "hours_ago": None}

    now = datetime.now(timezone.utc)
    last_inbound = contact.last_inbound_whatsapp_at
    if last_inbound.tzinfo is None:
        last_inbound = last_inbound.replace(tzinfo=timezone.utc)

    diff = now - last_inbound
    is_open = diff.total_seconds() < 86400

    return {
        "is_open": is_open,
        "requires_template": not is_open,
        "expires_at": (last_inbound + timedelta(hours=24)).isoformat() if is_open else None,
        "hours_ago": round(diff.total_seconds() / 3600, 1),
    }
