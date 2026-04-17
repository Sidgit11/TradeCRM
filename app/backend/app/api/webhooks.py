"""Webhook handlers — Gupshup WhatsApp, SendGrid Email, Stripe Billing, Clerk Auth."""
from datetime import datetime, timezone
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.integrations.gupshup import gupshup_service
from app.integrations.sendgrid_service import sendgrid_service
from app.models.tenant import Tenant
from app.models.contact import Contact
from app.models.message import Message, MessageEvent
from app.models.enums import ChannelType, MessageDirection, MessageStatus, MessageEventType

logger = get_logger("api.webhooks")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/gupshup", status_code=status.HTTP_200_OK)
async def gupshup_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Receive ALL Gupshup webhook events for ALL tenant apps. Always responds 200."""
    try:
        payload = await request.json()
    except Exception:
        logger.error("webhook:gupshup | INVALID_JSON — could not parse request body")
        return {"status": "invalid_payload"}

    try:
        event = await gupshup_service.parse_webhook(payload)
    except Exception as e:
        logger.error("webhook:gupshup | PARSE_FAILED | error=%s payload=%s", str(e), str(payload)[:200])
        return {"status": "parse_error"}

    app_name = event.get("app_name", "")
    kind = event.get("kind", "unknown")
    logger.info("webhook:gupshup | kind=%s app=%s", kind, app_name)

    try:
        if kind == "inbound_message":
            tenant = (await db.execute(
                select(Tenant).where(Tenant.gupshup_app_name == app_name)
            )).scalar_one_or_none()

            if not tenant:
                logger.warning("webhook:gupshup | UNKNOWN_APP | app=%s", app_name)
                return {"status": "unknown_app"}

            phone = event.get("phone", "")
            text = event.get("text", "")

            # Find or create contact by phone
            contact = (await db.execute(
                select(Contact).where(
                    Contact.tenant_id == tenant.id,
                    Contact.phone == phone,
                    Contact.is_deleted.is_(False),
                )
            )).scalar_one_or_none()

            if not contact:
                contact = (await db.execute(
                    select(Contact).where(
                        Contact.tenant_id == tenant.id,
                        Contact.phone == f"+{phone}",
                        Contact.is_deleted.is_(False),
                    )
                )).scalar_one_or_none()

            if not contact:
                contact = Contact(
                    tenant_id=tenant.id,
                    name=phone,
                    phone=phone,
                    whatsapp_number=phone,
                    source="discovery",
                    opted_in_whatsapp=True,
                )
                db.add(contact)
                await db.flush()
                logger.info("webhook:gupshup | CONTACT_CREATED | phone=%s tenant=%s", phone, str(tenant.id)[:8])

            contact.last_inbound_whatsapp_at = datetime.now(timezone.utc)

            message = Message(
                tenant_id=tenant.id,
                contact_id=contact.id,
                channel=ChannelType.whatsapp,
                direction=MessageDirection.inbound,
                body=text,
                status=MessageStatus.delivered,
                external_id=event.get("message_id", ""),
            )
            db.add(message)
            await db.commit()

            logger.info("webhook:gupshup | INBOUND | phone=%s text=%s tenant=%s",
                phone, text[:50], str(tenant.id)[:8])

        elif kind == "status_update":
            msg_status = event.get("status", "")
            ext_id = event.get("message_id", "")

            if ext_id:
                msg = (await db.execute(
                    select(Message).where(Message.external_id == ext_id)
                )).scalar_one_or_none()

                if msg:
                    status_map = {
                        "enqueued": MessageStatus.queued,
                        "sent": MessageStatus.sent,
                        "delivered": MessageStatus.delivered,
                        "read": MessageStatus.opened,
                        "failed": MessageStatus.failed,
                    }
                    if msg_status in status_map:
                        msg.status = status_map[msg_status]
                        if msg_status == "sent":
                            msg.sent_at = datetime.now(timezone.utc)
                        elif msg_status == "delivered":
                            msg.delivered_at = datetime.now(timezone.utc)
                        elif msg_status == "read":
                            msg.opened_at = datetime.now(timezone.utc)
                        elif msg_status == "failed":
                            msg.failed_reason = event.get("error_reason", "")

                    event_type = MessageEventType(msg_status) if msg_status in [e.value for e in MessageEventType] else MessageEventType.sent
                    db.add(MessageEvent(
                        message_id=msg.id,
                        tenant_id=msg.tenant_id,
                        event_type=event_type,
                        event_data=event.get("raw", {}),
                    ))
                    await db.commit()

            logger.info("webhook:gupshup | STATUS | msg=%s status=%s", ext_id[:12] if ext_id else "?", msg_status)

        elif kind == "template_status":
            logger.info("webhook:gupshup | TEMPLATE | name=%s status=%s", event.get("template_name"), event.get("status"))

        elif kind == "account_status":
            logger.info("webhook:gupshup | ACCOUNT | status=%s", event.get("status"))

    except Exception as e:
        logger.error("webhook:gupshup | PROCESSING_ERROR | kind=%s error=%s", kind, str(e), exc_info=True)
        # Always return 200 to prevent retry storms
        return {"status": "error", "detail": "Internal processing error"}

    return {"status": "received"}


@router.post("/sendgrid", status_code=status.HTTP_200_OK)
async def sendgrid_webhook(request: Request):
    """Receive SendGrid email webhook events. Always responds 200."""
    try:
        events: List[Dict[str, Any]] = await request.json()
    except Exception:
        logger.error("webhook:sendgrid | INVALID_JSON — could not parse request body")
        return {"status": "invalid_payload"}

    try:
        parsed = await sendgrid_service.parse_webhook(events)
        for event in parsed:
            logger.info("webhook:sendgrid | type=%s email=%s msg=%s",
                event.get("event_type"), event.get("email"), event.get("message_id", "")[:20])
        return {"status": "received", "count": len(parsed)}
    except Exception as e:
        logger.error("webhook:sendgrid | PROCESSING_ERROR | error=%s", str(e), exc_info=True)
        return {"status": "error"}


@router.post("/stripe", status_code=status.HTTP_200_OK)
async def stripe_webhook(request: Request):
    """Receive Stripe billing webhook events. Always responds 200."""
    try:
        payload = await request.body()
        logger.info("webhook:stripe | received payload_size=%d (placeholder)", len(payload))
    except Exception as e:
        logger.error("webhook:stripe | error=%s", str(e), exc_info=True)
    return {"status": "received"}
