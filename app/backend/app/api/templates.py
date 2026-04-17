"""Templates API — CRUD, AI generation, variable registry."""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.message_template import MessageTemplate
from app.models.tenant import Tenant
from app.models.enums import TemplateChannel, TemplateCategory
from app.schemas.templates import (
    TemplateCreate, TemplateUpdate, TemplateResponse,
    TemplateGenerateRequest, TemplateRefineRequest, TemplateGenerateResponse,
)
from app.services.template_variables import detect_variables, get_variable_list

logger = get_logger("api.templates")
router = APIRouter(prefix="/templates", tags=["templates"])


def _template_response(t: MessageTemplate) -> TemplateResponse:
    return TemplateResponse(
        id=str(t.id), tenant_id=str(t.tenant_id),
        created_by=str(t.created_by) if t.created_by else None,
        name=t.name, channel=t.channel.value, category=t.category.value,
        subject=t.subject, body=t.body, body_format=t.body_format,
        variables=t.variables or [],
        description=t.description,
        is_archived=t.is_archived, is_default=t.is_default,
        ai_generated=t.ai_generated, ai_prompt=t.ai_prompt,
        last_used_at=t.last_used_at.isoformat() if t.last_used_at else None,
        usage_count=t.usage_count,
        created_at=t.created_at.isoformat(), updated_at=t.updated_at.isoformat(),
    )


# ── Variable registry ────────────────────────────────────────────────

@router.get("/variables")
async def list_variables():
    """Return canonical variable list for frontend."""
    return get_variable_list()


# ── CRUD ──────────────────────────────────────────────────────────────

@router.get("", response_model=list)
async def list_templates(
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
    channel: Optional[str] = None,
    category: Optional[str] = None,
    include_archived: bool = False,
):
    query = select(MessageTemplate).where(MessageTemplate.tenant_id == tenant_id)

    if not include_archived:
        query = query.where(MessageTemplate.is_archived.is_(False))
    if channel:
        query = query.where(MessageTemplate.channel == channel)
    if category:
        query = query.where(MessageTemplate.category == category)

    result = await db.execute(query.order_by(desc(MessageTemplate.updated_at)))
    return [_template_response(t) for t in result.scalars().all()]


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id, MessageTemplate.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    return _template_response(t)


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(
    body: TemplateCreate, user: CurrentUser,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    # Auto-detect variables
    all_text = f"{body.subject or ''} {body.body}"
    variables = detect_variables(all_text)

    t = MessageTemplate(
        tenant_id=tenant_id, created_by=user.id,
        name=body.name,
        channel=TemplateChannel(body.channel),
        category=TemplateCategory(body.category) if body.category in [c.value for c in TemplateCategory] else TemplateCategory.custom,
        subject=body.subject, body=body.body,
        description=body.description,
        variables=variables,
        ai_generated=body.ai_generated,
        ai_prompt=body.ai_prompt,
        is_default=body.is_default,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    logger.info("Template created: id=%s name=%s channel=%s", t.id, t.name, t.channel.value)
    return _template_response(t)


@router.put("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: uuid.UUID, body: TemplateUpdate,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id, MessageTemplate.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")

    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "category" and value:
            value = TemplateCategory(value) if value in [c.value for c in TemplateCategory] else t.category
        setattr(t, field, value)

    # Re-detect variables if body or subject changed
    if body.body is not None or body.subject is not None:
        all_text = f"{t.subject or ''} {t.body}"
        t.variables = detect_variables(all_text)

    await db.commit()
    await db.refresh(t)
    return _template_response(t)


@router.delete("/{template_id}", status_code=204)
async def archive_template(
    template_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    t = (await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id, MessageTemplate.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Template not found")
    t.is_archived = True
    await db.commit()
    logger.info("Template archived: id=%s", template_id)


@router.post("/{template_id}/duplicate", response_model=TemplateResponse, status_code=201)
async def duplicate_template(
    template_id: uuid.UUID, user: CurrentUser,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    original = (await db.execute(
        select(MessageTemplate).where(
            MessageTemplate.id == template_id, MessageTemplate.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not original:
        raise HTTPException(status_code=404, detail="Template not found")

    clone = MessageTemplate(
        tenant_id=tenant_id, created_by=user.id,
        name=f"{original.name} (Copy)",
        channel=original.channel, category=original.category,
        subject=original.subject, body=original.body,
        body_format=original.body_format,
        variables=original.variables,
        description=original.description,
        ai_generated=original.ai_generated,
        ai_prompt=original.ai_prompt,
    )
    db.add(clone)
    await db.commit()
    await db.refresh(clone)
    logger.info("Template duplicated: %s -> %s", template_id, clone.id)
    return _template_response(clone)


# ── AI Generation ────────────────────────────────────────────────────

@router.post("/generate", response_model=TemplateGenerateResponse)
async def generate_template(
    body: TemplateGenerateRequest,
    tenant_id: CurrentTenantId, db: AsyncSession = Depends(get_db),
):
    from app.agents.template_author_agent import generate

    # Get tenant context
    tenant = (await db.execute(select(Tenant).where(Tenant.id == tenant_id))).scalar_one_or_none()
    tenant_name = tenant.company_name if tenant else None
    tenant_commodities = tenant.commodities if tenant else None

    result = await generate(
        channel=body.channel, category=body.category,
        tone=body.tone, context=body.context,
        variables_hint=body.variables_hint,
        tenant_name=tenant_name,
        tenant_commodities=tenant_commodities,
    )

    return TemplateGenerateResponse(
        subject=result.get("subject"),
        body=result.get("body", ""),
        variables_detected=result.get("variables_detected", []),
    )


@router.post("/refine", response_model=TemplateGenerateResponse)
async def refine_template(body: TemplateRefineRequest):
    from app.agents.template_author_agent import refine

    result = await refine(
        current_body=body.current_body,
        current_subject=body.current_subject,
        action=body.action,
        channel=body.channel,
    )

    all_text = f"{result.get('subject', '') or ''} {result.get('body', '')}"
    return TemplateGenerateResponse(
        subject=result.get("subject"),
        body=result.get("body", ""),
        variables_detected=detect_variables(all_text),
    )
