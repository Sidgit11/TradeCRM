from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentUser, CurrentTenantId, require_role
from app.models.enums import PlanType, UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import (
    InviteMemberRequest,
    LoginRequest,
    MeResponse,
    MemberResponse,
    RefreshRequest,
    SignupRequest,
    TenantResponse,
    TenantUpdateRequest,
    TokenResponse,
    UpdateMemberRoleRequest,
    UserResponse,
)

logger = get_logger("api.auth")
router = APIRouter(prefix="/auth", tags=["auth"])
tenant_router = APIRouter(prefix="/tenants", tags=["tenants"])


def _user_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        tenant_id=str(user.tenant_id),
        email=user.email,
        name=user.name,
        role=user.role.value,
        is_active=user.is_active,
        last_active_at=user.last_active_at.isoformat() if user.last_active_at else None,
        created_at=user.created_at.isoformat(),
    )


def _tenant_response(tenant: Tenant) -> TenantResponse:
    return TenantResponse(
        id=str(tenant.id),
        company_name=tenant.company_name,
        domain=tenant.domain,
        plan=tenant.plan.value,
        commodities=tenant.commodities or [],
        target_markets=tenant.target_markets or [],
        certifications=tenant.certifications or [],
        about=tenant.about,
        created_at=tenant.created_at.isoformat(),
    )


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Create a new tenant and admin user via Supabase Auth."""
    # Check if email already exists
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create tenant
    tenant = Tenant(
        company_name=body.company_name,
        plan=PlanType.free_trial,
    )
    db.add(tenant)
    await db.flush()

    # Create admin user
    # In production, this would call Supabase Auth to create the user first
    # and use the returned supabase_user_id. For now, we generate a placeholder.
    user = User(
        tenant_id=tenant.id,
        supabase_user_id=f"sup_{uuid.uuid4().hex[:24]}",
        email=body.email,
        name=body.name,
        role=UserRole.admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(tenant)
    await db.refresh(user)

    logger.info("New signup: tenant=%s user=%s email=%s", tenant.id, user.id, body.email)

    # In production, tokens come from Supabase Auth
    return TokenResponse(
        access_token=f"placeholder_access_{user.supabase_user_id}",
        refresh_token=f"placeholder_refresh_{user.supabase_user_id}",
        user=_user_response(user),
        tenant=_tenant_response(tenant),
    )


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate user via Supabase Auth and return tokens."""
    # In production, this calls Supabase Auth signInWithPassword
    result = await db.execute(select(User).where(User.email == body.email, User.is_active.is_(True)))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Load tenant
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one()

    logger.info("Login: user=%s tenant=%s", user.id, tenant.id)

    return TokenResponse(
        access_token=f"placeholder_access_{user.supabase_user_id}",
        refresh_token=f"placeholder_refresh_{user.supabase_user_id}",
        user=_user_response(user),
        tenant=_tenant_response(tenant),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    """Refresh access token using refresh token. In production, delegates to Supabase Auth."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Token refresh will be implemented with Supabase Auth integration",
    )


@router.get("/me", response_model=MeResponse)
async def get_me(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    """Get current authenticated user and tenant info."""
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one()

    return MeResponse(
        user=_user_response(user),
        tenant=_tenant_response(tenant),
    )


# --- Tenant Management ---


@tenant_router.put("/settings", response_model=TenantResponse)
async def update_tenant_settings(
    body: TenantUpdateRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update tenant company profile. Admin only."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    tenant_result = await db.execute(select(Tenant).where(Tenant.id == user.tenant_id))
    tenant = tenant_result.scalar_one()

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)

    logger.info("Tenant settings updated: tenant=%s fields=%s", tenant.id, list(update_data.keys()))
    return _tenant_response(tenant)


@tenant_router.post("/invite", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    body: InviteMemberRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Invite a team member. Admin only."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    # Check for existing member
    existing = await db.execute(
        select(User).where(User.email == body.email, User.tenant_id == user.tenant_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Member already exists")

    role = UserRole.admin if body.role == "admin" else UserRole.member
    new_user = User(
        tenant_id=user.tenant_id,
        supabase_user_id=f"sup_{uuid.uuid4().hex[:24]}",
        email=body.email,
        name=body.name,
        role=role,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info("Member invited: tenant=%s new_user=%s email=%s", user.tenant_id, new_user.id, body.email)
    return MemberResponse(
        id=str(new_user.id),
        email=new_user.email,
        name=new_user.name,
        role=new_user.role.value,
        is_active=new_user.is_active,
        last_active_at=None,
        created_at=new_user.created_at.isoformat(),
    )


@tenant_router.get("/members", response_model=list)
async def list_members(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """List all team members for the current tenant."""
    result = await db.execute(
        select(User).where(User.tenant_id == user.tenant_id, User.is_active.is_(True))
    )
    users = result.scalars().all()
    return [
        MemberResponse(
            id=str(u.id),
            email=u.email,
            name=u.name,
            role=u.role.value,
            is_active=u.is_active,
            last_active_at=u.last_active_at.isoformat() if u.last_active_at else None,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]


@tenant_router.put("/members/{member_id}/role", response_model=MemberResponse)
async def update_member_role(
    member_id: uuid.UUID,
    body: UpdateMemberRoleRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Change a team member's role. Admin only."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    result = await db.execute(
        select(User).where(User.id == member_id, User.tenant_id == user.tenant_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    member.role = UserRole.admin if body.role == "admin" else UserRole.member
    await db.commit()
    await db.refresh(member)

    logger.info("Member role updated: member=%s role=%s", member.id, member.role.value)
    return MemberResponse(
        id=str(member.id),
        email=member.email,
        name=member.name,
        role=member.role.value,
        is_active=member.is_active,
        last_active_at=member.last_active_at.isoformat() if member.last_active_at else None,
        created_at=member.created_at.isoformat(),
    )


@tenant_router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Remove a team member (soft-deactivate). Admin only. Cannot remove self."""
    if user.role != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")

    if member_id == user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove yourself")

    result = await db.execute(
        select(User).where(User.id == member_id, User.tenant_id == user.tenant_id)
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    member.is_active = False
    await db.commit()
    logger.info("Member removed: member=%s tenant=%s", member_id, user.tenant_id)
