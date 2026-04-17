"""Billing API — credits, usage tracking, Stripe integration."""
from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.tenant import Tenant
from app.models.message import Message
from app.models.activity import CreditTransaction, AgentTask
from app.models.enums import UserRole
from app.config import settings

logger = get_logger("api.billing")
router = APIRouter(prefix="/billing", tags=["billing"])

# Plan limits
PLAN_LIMITS = {
    "free_trial": {"messages": 50, "enrichments": 10, "name": "Free Trial"},
    "starter": {"messages": 500, "enrichments": 100, "name": "Starter — $199/mo"},
    "growth": {"messages": 2000, "enrichments": 500, "name": "Growth — $499/mo"},
    "pro": {"messages": 10000, "enrichments": -1, "name": "Pro — $999/mo"},  # -1 = unlimited
}


class CreditBalance(BaseModel):
    plan: str
    plan_name: str
    messages_used: int
    messages_limit: int
    enrichments_used: int
    enrichments_limit: int
    credits_remaining: int


@router.get("/credits", response_model=CreditBalance)
async def get_credit_balance(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get current credit balance and usage."""
    tenant = (await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )).scalar_one()

    plan = tenant.plan.value
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free_trial"])

    # Count messages sent this month
    from datetime import datetime, timezone
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    messages_used = (await db.execute(
        select(func.count()).where(
            Message.tenant_id == tenant_id,
            Message.created_at >= month_start,
        )
    )).scalar() or 0

    # Count enrichments this month
    from app.models.enums import AgentTaskType
    enrichments_used = (await db.execute(
        select(func.count()).where(
            AgentTask.tenant_id == tenant_id,
            AgentTask.task_type.in_([AgentTaskType.company_research, AgentTaskType.contact_enrichment]),
            AgentTask.created_at >= month_start,
        )
    )).scalar() or 0

    msg_limit = limits["messages"]
    enr_limit = limits["enrichments"]
    credits_remaining = max(0, msg_limit - messages_used) if msg_limit > 0 else 999999

    return CreditBalance(
        plan=plan,
        plan_name=limits["name"],
        messages_used=messages_used,
        messages_limit=msg_limit,
        enrichments_used=enrichments_used,
        enrichments_limit=enr_limit,
        credits_remaining=credits_remaining,
    )


@router.get("/usage")
async def get_usage(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Current month usage breakdown."""
    from datetime import datetime, timezone
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    messages = (await db.execute(
        select(func.count()).where(Message.tenant_id == tenant_id, Message.created_at >= month_start)
    )).scalar() or 0

    from app.models.enums import AgentTaskType
    ai_tasks = (await db.execute(
        select(func.count()).where(AgentTask.tenant_id == tenant_id, AgentTask.created_at >= month_start)
    )).scalar() or 0

    from app.models.contact import Contact
    contacts_stored = (await db.execute(
        select(func.count()).where(Contact.tenant_id == tenant_id, Contact.is_deleted.is_(False))
    )).scalar() or 0

    return {
        "period_start": month_start.isoformat(),
        "messages_sent": messages,
        "ai_tasks_run": ai_tasks,
        "contacts_stored": contacts_stored,
    }


@router.post("/create-checkout")
async def create_checkout_session(
    user: CurrentUser,
    tenant_id: CurrentTenantId,
):
    """Create Stripe Checkout session. Placeholder — wire up Stripe when keys are available."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")

    if not settings.STRIPE_SECRET_KEY:
        logger.warning("Stripe not configured")
        return {
            "url": None,
            "message": "Stripe billing not yet configured. Contact support to upgrade.",
        }

    # TODO: create actual Stripe Checkout session
    logger.info("Checkout session requested: tenant=%s", tenant_id)
    return {"url": "https://checkout.stripe.com/placeholder", "message": "Redirect to Stripe"}


@router.post("/create-portal")
async def create_portal_session(
    user: CurrentUser,
    tenant_id: CurrentTenantId,
):
    """Create Stripe Customer Portal session for subscription management."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin only")

    if not settings.STRIPE_SECRET_KEY:
        return {"url": None, "message": "Stripe billing not yet configured."}

    logger.info("Portal session requested: tenant=%s", tenant_id)
    return {"url": "https://billing.stripe.com/placeholder"}
