"""Dashboard API — stats, activity feed, pending approvals."""
from typing import Optional
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId
from app.models.message import Message
from app.models.reply_suggestion import ReplySuggestion
from app.models.activity import ActivityLog
from app.models.enums import MessageDirection, SuggestionStatus

logger = get_logger("api.dashboard")
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Today's key metrics."""
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    messages_sent = (await db.execute(
        select(func.count()).where(
            Message.tenant_id == tenant_id,
            Message.direction == MessageDirection.outbound,
            Message.created_at >= today_start,
        )
    )).scalar() or 0

    replies_received = (await db.execute(
        select(func.count()).where(
            Message.tenant_id == tenant_id,
            Message.direction == MessageDirection.inbound,
            Message.created_at >= today_start,
        )
    )).scalar() or 0

    pending_approvals = (await db.execute(
        select(func.count()).where(
            ReplySuggestion.tenant_id == tenant_id,
            ReplySuggestion.status == SuggestionStatus.pending,
        )
    )).scalar() or 0

    # Follow-ups due: sequences with next_action_at <= now
    from app.models.sequence import Sequence
    from app.models.enums import SequenceStatus
    followups_due = (await db.execute(
        select(func.count()).where(
            Sequence.tenant_id == tenant_id,
            Sequence.status == SequenceStatus.active,
            Sequence.next_action_at <= datetime.now(timezone.utc),
        )
    )).scalar() or 0

    return {
        "messages_sent_today": messages_sent,
        "replies_received_today": replies_received,
        "pending_approvals": pending_approvals,
        "followups_due": followups_due,
    }


@router.get("/activity")
async def get_activity_feed(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=50),
    skip: int = Query(0, ge=0),
):
    """Recent activity feed (agent + user actions)."""
    result = await db.execute(
        select(ActivityLog)
        .where(ActivityLog.tenant_id == tenant_id)
        .order_by(desc(ActivityLog.created_at))
        .offset(skip).limit(limit)
    )
    activities = result.scalars().all()

    return [
        {
            "id": str(a.id),
            "actor_type": a.actor_type.value,
            "actor_id": str(a.actor_id) if a.actor_id else None,
            "action": a.action,
            "entity_type": a.entity_type,
            "entity_id": str(a.entity_id) if a.entity_id else None,
            "detail": a.detail,
            "created_at": a.created_at.isoformat(),
        }
        for a in activities
    ]


@router.get("/pending-approvals")
async def get_pending_approvals(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(10, ge=1, le=20),
):
    """List AI reply suggestions awaiting approval."""
    result = await db.execute(
        select(ReplySuggestion)
        .where(
            ReplySuggestion.tenant_id == tenant_id,
            ReplySuggestion.status == SuggestionStatus.pending,
        )
        .order_by(desc(ReplySuggestion.created_at))
        .limit(limit)
    )
    suggestions = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "message_id": str(s.message_id),
            "classification": s.classification.value,
            "suggested_reply_text": s.suggested_reply_text,
            "explanation": s.explanation,
            "confidence": float(s.confidence),
            "created_at": s.created_at.isoformat(),
        }
        for s in suggestions
    ]
