"""Clerk webhook handler — provisions users only if whitelisted."""
from typing import Any, Dict

from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.models.tenant import Tenant
from app.models.user import User
from app.models.whitelist import AllowedEmail
from app.models.enums import PlanType, UserRole

logger = get_logger("api.clerk_webhook")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _is_email_whitelisted(db: AsyncSession, email: str) -> bool:
    """Check if an email is in the whitelist."""
    result = await db.execute(
        select(AllowedEmail).where(
            AllowedEmail.email == email.lower(),
            AllowedEmail.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none() is not None


@router.post("/clerk", status_code=200)
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle Clerk webhook events.
    Users are only approved if their email is in the allowed_emails table.
    """
    payload = await request.json()
    event_type = payload.get("type", "")
    data = payload.get("data", {})

    logger.info("Clerk webhook: type=%s", event_type)

    if event_type == "user.created":
        await _handle_user_created(db, data)
    elif event_type == "user.updated":
        await _handle_user_updated(db, data)
    elif event_type == "user.deleted":
        await _handle_user_deleted(db, data)

    return {"status": "received"}


async def _handle_user_created(db: AsyncSession, data: Dict[str, Any]) -> None:
    """Create tenant + user. Only approve if email is whitelisted."""
    clerk_user_id = data.get("id", "")
    email_addresses = data.get("email_addresses", [])
    email = email_addresses[0].get("email_address", "") if email_addresses else ""
    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    name = f"{first_name} {last_name}".strip() or email.split("@")[0]

    if not clerk_user_id or not email:
        logger.warning("Clerk user.created missing id or email, skipping")
        return

    email = email.lower()

    # Check if already exists
    existing = await db.execute(
        select(User).where(User.supabase_user_id == clerk_user_id)
    )
    if existing.scalar_one_or_none():
        logger.info("User already exists for clerk_id=%s, skipping", clerk_user_id)
        return

    # Check whitelist
    is_whitelisted = await _is_email_whitelisted(db, email)

    # Create tenant
    domain = email.split("@")[1] if "@" in email else ""
    company_name = domain.split(".")[0].title() if domain else name

    tenant = Tenant(
        company_name=company_name,
        domain=domain,
        plan=PlanType.free_trial,
    )
    db.add(tenant)
    await db.flush()

    # Create user — only approved if whitelisted
    user = User(
        tenant_id=tenant.id,
        supabase_user_id=clerk_user_id,
        email=email,
        name=name,
        role=UserRole.admin,
        is_approved=is_whitelisted,
    )
    db.add(user)
    await db.commit()

    if is_whitelisted:
        logger.info(
            "Whitelisted user provisioned: clerk_id=%s email=%s tenant=%s",
            clerk_user_id, email, tenant.id,
        )
    else:
        logger.info(
            "User created but NOT approved (not whitelisted): clerk_id=%s email=%s",
            clerk_user_id, email,
        )


async def _handle_user_updated(db: AsyncSession, data: Dict[str, Any]) -> None:
    """Sync profile changes from Clerk."""
    clerk_user_id = data.get("id", "")
    result = await db.execute(
        select(User).where(User.supabase_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    email_addresses = data.get("email_addresses", [])
    if email_addresses:
        user.email = email_addresses[0].get("email_address", user.email)

    first_name = data.get("first_name", "")
    last_name = data.get("last_name", "")
    if first_name or last_name:
        user.name = f"{first_name} {last_name}".strip()

    await db.commit()
    logger.info("Clerk user synced: clerk_id=%s", clerk_user_id)


async def _handle_user_deleted(db: AsyncSession, data: Dict[str, Any]) -> None:
    """Deactivate user when deleted from Clerk."""
    clerk_user_id = data.get("id", "")
    result = await db.execute(
        select(User).where(User.supabase_user_id == clerk_user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        return

    user.is_active = False
    await db.commit()
    logger.info("Clerk user deactivated: clerk_id=%s", clerk_user_id)
