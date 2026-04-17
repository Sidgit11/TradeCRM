"""Inbox API — unified conversations, reply management, AI suggestions."""
from typing import Optional
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.contact import Contact
from app.models.message import Message
from app.models.reply_suggestion import ReplySuggestion
from app.models.enums import (
    ChannelType, MessageDirection, MessageStatus, SuggestionStatus,
)
from app.schemas.inbox import (
    ConversationSummary, MessageResponse, ReplyRequest, SuggestionResponse,
)

logger = get_logger("api.inbox")
router = APIRouter(prefix="/inbox", tags=["inbox"])


def _message_response(m: Message) -> MessageResponse:
    return MessageResponse(
        id=str(m.id), channel=m.channel.value, direction=m.direction.value,
        subject=m.subject, body=m.body, status=m.status.value,
        sent_at=m.sent_at.isoformat() if m.sent_at else None,
        delivered_at=m.delivered_at.isoformat() if m.delivered_at else None,
        opened_at=m.opened_at.isoformat() if m.opened_at else None,
        created_at=m.created_at.isoformat(),
    )


@router.get("/conversations", response_model=list)
async def list_conversations(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    channel: Optional[str] = None,
    classification: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
):
    """List conversations grouped by contact, with last message preview."""
    # Get contacts with messages, ordered by most recent message
    subq = (
        select(
            Message.contact_id,
            func.max(Message.created_at).label("last_msg_at"),
            func.count(Message.id).label("msg_count"),
        )
        .where(Message.tenant_id == tenant_id)
        .group_by(Message.contact_id)
        .subquery()
    )

    query = (
        select(Contact, subq.c.last_msg_at)
        .join(subq, Contact.id == subq.c.contact_id)
        .where(Contact.tenant_id == tenant_id, Contact.is_deleted.is_(False))
        .order_by(desc(subq.c.last_msg_at))
        .limit(limit)
    )

    result = await db.execute(query)
    conversations = []

    for contact, last_msg_at in result.all():
        # Get last message
        last_msg_result = await db.execute(
            select(Message)
            .where(Message.contact_id == contact.id, Message.tenant_id == tenant_id)
            .order_by(desc(Message.created_at))
            .limit(1)
        )
        last_msg = last_msg_result.scalar_one_or_none()

        # Determine channel
        channels_result = await db.execute(
            select(Message.channel)
            .where(Message.contact_id == contact.id, Message.tenant_id == tenant_id)
            .distinct()
        )
        channels = [row[0].value for row in channels_result.all()]
        conv_channel = "multi" if len(channels) > 1 else (channels[0] if channels else "email")

        if channel and conv_channel != channel and channel != "all":
            continue

        # Count unread (inbound messages not yet opened)
        unread_result = await db.execute(
            select(func.count()).where(
                Message.contact_id == contact.id,
                Message.tenant_id == tenant_id,
                Message.direction == MessageDirection.inbound,
                Message.opened_at.is_(None),
            )
        )
        unread = unread_result.scalar() or 0

        # Get latest classification
        cls_result = await db.execute(
            select(ReplySuggestion.classification)
            .join(Message, ReplySuggestion.message_id == Message.id)
            .where(Message.contact_id == contact.id, ReplySuggestion.tenant_id == tenant_id)
            .order_by(desc(ReplySuggestion.created_at))
            .limit(1)
        )
        cls_row = cls_result.first()
        latest_classification = cls_row[0].value if cls_row else None

        if classification and latest_classification != classification:
            continue

        conversations.append(ConversationSummary(
            contact_id=str(contact.id),
            contact_name=contact.name,
            company_name=contact.company_name,
            last_message_preview=last_msg.body[:100] if last_msg else None,
            last_message_at=last_msg_at.isoformat() if last_msg_at else None,
            channel=conv_channel,
            unread_count=unread,
            classification=latest_classification,
        ))

    return conversations


@router.get("/conversations/{contact_id}", response_model=list)
async def get_conversation_thread(
    contact_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=200),
):
    """Get full message thread for a contact (all channels, chronological)."""
    result = await db.execute(
        select(Message)
        .where(Message.contact_id == contact_id, Message.tenant_id == tenant_id)
        .order_by(Message.created_at)
        .limit(limit)
    )
    messages = result.scalars().all()

    # Mark inbound messages as read
    for msg in messages:
        if msg.direction == MessageDirection.inbound and msg.opened_at is None:
            msg.opened_at = datetime.now(timezone.utc)
    await db.commit()

    return [_message_response(m) for m in messages]


@router.post("/conversations/{contact_id}/reply", status_code=201)
async def send_reply(
    contact_id: uuid.UUID, body: ReplyRequest,
    user: CurrentUser, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Send a reply message to a contact."""
    contact = (await db.execute(
        select(Contact).where(Contact.id == contact_id, Contact.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    message = Message(
        tenant_id=tenant_id, contact_id=contact_id, sent_by=user.id,
        channel=ChannelType(body.channel), direction=MessageDirection.outbound,
        subject=body.subject, body=body.body,
        status=MessageStatus.queued,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    logger.info("Reply queued: contact=%s channel=%s msg=%s", contact_id, body.channel, message.id)

    # TODO: dispatch to Celery for actual sending via Gupshup/SendGrid

    return _message_response(message)


@router.post("/conversations/{contact_id}/close", status_code=200)
async def close_conversation(
    contact_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Close a conversation (mark all inbound as read)."""
    result = await db.execute(
        select(Message).where(
            Message.contact_id == contact_id, Message.tenant_id == tenant_id,
            Message.direction == MessageDirection.inbound, Message.opened_at.is_(None),
        )
    )
    for msg in result.scalars().all():
        msg.opened_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "closed"}


@router.get("/suggestions", response_model=list)
async def list_pending_suggestions(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
):
    """List pending AI reply suggestions."""
    result = await db.execute(
        select(ReplySuggestion)
        .where(
            ReplySuggestion.tenant_id == tenant_id,
            ReplySuggestion.status == SuggestionStatus.pending,
        )
        .order_by(desc(ReplySuggestion.created_at))
        .limit(limit)
    )
    return [
        SuggestionResponse(
            id=str(s.id), message_id=str(s.message_id),
            classification=s.classification.value,
            suggested_reply_text=s.suggested_reply_text,
            explanation=s.explanation,
            confidence=float(s.confidence),
            status=s.status.value,
            created_at=s.created_at.isoformat(),
        )
        for s in result.scalars().all()
    ]


@router.post("/suggestions/{suggestion_id}/approve", status_code=200)
async def approve_suggestion(
    suggestion_id: uuid.UUID, tenant_id: CurrentTenantId,
    user: CurrentUser, db: AsyncSession = Depends(get_db),
):
    """Approve an AI suggestion and queue it for sending."""
    suggestion = (await db.execute(
        select(ReplySuggestion).where(
            ReplySuggestion.id == suggestion_id, ReplySuggestion.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    suggestion.status = SuggestionStatus.approved
    suggestion.actioned_at = datetime.now(timezone.utc)
    await db.commit()

    logger.info("Suggestion approved: id=%s", suggestion_id)
    return {"status": "approved", "suggestion_id": str(suggestion_id)}


@router.post("/suggestions/{suggestion_id}/reject", status_code=200)
async def reject_suggestion(
    suggestion_id: uuid.UUID, tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    suggestion = (await db.execute(
        select(ReplySuggestion).where(
            ReplySuggestion.id == suggestion_id, ReplySuggestion.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not suggestion:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    suggestion.status = SuggestionStatus.rejected
    suggestion.actioned_at = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "rejected"}
