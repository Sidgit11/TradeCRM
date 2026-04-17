"""Admin API — whitelist management, user approval. Internal use only."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentUser
from app.models.user import User
from app.models.whitelist import AllowedEmail
from app.models.enums import UserRole

logger = get_logger("api.admin")
router = APIRouter(prefix="/admin", tags=["admin"])


class WhitelistAddRequest(BaseModel):
    email: EmailStr
    note: str = ""


class WhitelistResponse(BaseModel):
    id: str
    email: str
    note: str
    is_active: bool
    created_at: str


class PendingUserResponse(BaseModel):
    id: str
    email: str
    name: str
    is_approved: bool
    created_at: str


def _require_superadmin(user: User) -> None:
    """For now, any admin can manage whitelist. Tighten later with a superadmin flag."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Admin access required")


# --- Whitelist Management ---


@router.post("/whitelist", response_model=WhitelistResponse, status_code=201)
async def add_to_whitelist(
    body: WhitelistAddRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Add an email to the whitelist. If a pending user exists with this email, auto-approve them."""
    _require_superadmin(user)

    email = body.email.lower()

    # Check if already whitelisted
    existing = await db.execute(
        select(AllowedEmail).where(AllowedEmail.email == email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already whitelisted")

    entry = AllowedEmail(email=email, note=body.note)
    db.add(entry)

    # Auto-approve any existing user with this email
    user_result = await db.execute(
        select(User).where(User.email == email, User.is_approved.is_(False))
    )
    pending_user = user_result.scalar_one_or_none()
    if pending_user:
        pending_user.is_approved = True
        logger.info("Auto-approved pending user: email=%s user=%s", email, pending_user.id)

    await db.commit()
    await db.refresh(entry)

    logger.info("Email whitelisted: %s by admin=%s", email, user.id)
    return WhitelistResponse(
        id=str(entry.id), email=entry.email, note=entry.note or "",
        is_active=entry.is_active, created_at=entry.created_at.isoformat(),
    )


@router.get("/whitelist", response_model=list)
async def list_whitelist(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """List all whitelisted emails."""
    _require_superadmin(user)

    result = await db.execute(
        select(AllowedEmail).where(AllowedEmail.is_active.is_(True))
    )
    return [
        WhitelistResponse(
            id=str(e.id), email=e.email, note=e.note or "",
            is_active=e.is_active, created_at=e.created_at.isoformat(),
        )
        for e in result.scalars().all()
    ]


@router.delete("/whitelist/{entry_id}", status_code=204)
async def remove_from_whitelist(
    entry_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Remove an email from the whitelist (deactivate, not delete)."""
    _require_superadmin(user)

    entry = (await db.execute(
        select(AllowedEmail).where(AllowedEmail.id == entry_id)
    )).scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")

    entry.is_active = False
    await db.commit()
    logger.info("Email removed from whitelist: %s by admin=%s", entry.email, user.id)


# --- User Approval ---


@router.get("/pending-users", response_model=list)
async def list_pending_users(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """List users who signed up but are not yet approved."""
    _require_superadmin(user)

    result = await db.execute(
        select(User).where(
            User.is_approved.is_(False),
            User.is_active.is_(True),
        )
    )
    return [
        PendingUserResponse(
            id=str(u.id), email=u.email, name=u.name,
            is_approved=u.is_approved, created_at=u.created_at.isoformat(),
        )
        for u in result.scalars().all()
    ]


@router.post("/approve-user/{user_id}", status_code=200)
async def approve_user(
    user_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Manually approve a user and add their email to the whitelist."""
    _require_superadmin(user)

    target = (await db.execute(
        select(User).where(User.id == user_id)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_approved = True

    # Also whitelist their email for future logins
    existing_wl = await db.execute(
        select(AllowedEmail).where(AllowedEmail.email == target.email)
    )
    if not existing_wl.scalar_one_or_none():
        db.add(AllowedEmail(email=target.email, note=f"Auto-added on approval by {user.email}"))

    await db.commit()
    logger.info("User approved: user=%s email=%s by admin=%s", user_id, target.email, user.id)
    return {"status": "approved", "user_id": str(user_id), "email": target.email}


@router.post("/reject-user/{user_id}", status_code=200)
async def reject_user(
    user_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Reject and deactivate a pending user."""
    _require_superadmin(user)

    target = (await db.execute(
        select(User).where(User.id == user_id)
    )).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.is_active = False
    target.is_approved = False
    await db.commit()
    logger.info("User rejected: user=%s email=%s by admin=%s", user_id, target.email, user.id)
    return {"status": "rejected", "user_id": str(user_id)}
