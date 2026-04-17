import uuid
from typing import Annotated, Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwk, jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.logging_config import get_logger
from app.models.user import User
from app.models.tenant import Tenant
from app.models.whitelist import AllowedEmail
from app.models.enums import UserRole, PlanType

logger = get_logger("middleware.tenant")
security = HTTPBearer()

_jwks_cache: Optional[dict] = None


async def _get_jwks() -> dict:
    """Fetch and cache Clerk's JWKS public keys."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache

    jwks_url = f"{settings.CLERK_JWT_ISSUER}/.well-known/jwks.json"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url, timeout=10)
            if response.status_code == 200:
                _jwks_cache = response.json()
                logger.info("Clerk JWKS fetched successfully")
                return _jwks_cache
    except Exception as e:
        logger.error("Failed to fetch Clerk JWKS: %s", str(e))

    return {"keys": []}


def _get_signing_key(jwks_data: dict, token: str) -> Optional[str]:
    """Extract the correct public key from JWKS based on the token's kid header."""
    try:
        headers = jwt.get_unverified_headers(token)
        kid = headers.get("kid")
    except JWTError:
        return None

    for key_data in jwks_data.get("keys", []):
        if key_data.get("kid") == kid:
            return jwk.construct(key_data).to_pem().decode("utf-8")

    return None


async def _auto_provision_user(
    db: AsyncSession,
    clerk_user_id: str,
    email: str,
    name: str,
) -> Optional[User]:
    """
    Auto-provision a user if their email is whitelisted.
    Creates tenant + user on first login — no webhook needed.
    """
    email_lower = email.lower()

    # Check whitelist
    wl_result = await db.execute(
        select(AllowedEmail).where(
            AllowedEmail.email == email_lower,
            AllowedEmail.is_active.is_(True),
        )
    )
    is_whitelisted = wl_result.scalar_one_or_none() is not None

    # Check if there's an existing user with placeholder ID for this email
    existing = await db.execute(
        select(User).where(User.email == email_lower, User.is_active.is_(True))
    )
    existing_user = existing.scalar_one_or_none()

    if existing_user:
        # Link the real Clerk ID to the existing user
        existing_user.supabase_user_id = clerk_user_id
        if is_whitelisted:
            existing_user.is_approved = True
        await db.commit()
        await db.refresh(existing_user)
        logger.info("Linked clerk_id=%s to existing user=%s email=%s", clerk_user_id, existing_user.id, email)
        return existing_user

    # Create new tenant + user
    domain = email_lower.split("@")[1] if "@" in email_lower else ""
    company_name = domain.split(".")[0].title() if domain else name

    tenant = Tenant(
        company_name=company_name,
        domain=domain,
        plan=PlanType.free_trial,
    )
    db.add(tenant)
    await db.flush()

    user = User(
        tenant_id=tenant.id,
        supabase_user_id=clerk_user_id,
        email=email_lower,
        name=name or email_lower.split("@")[0],
        role=UserRole.admin,
        is_approved=is_whitelisted,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info(
        "Auto-provisioned user: clerk_id=%s email=%s approved=%s tenant=%s",
        clerk_user_id, email, is_whitelisted, tenant.id,
    )
    return user


async def _get_dev_user(db: AsyncSession) -> User:
    """Return the first active approved admin user — for DEV_MODE only."""
    result = await db.execute(
        select(User).where(User.is_active.is_(True), User.is_approved.is_(True)).limit(1)
    )
    user = result.scalar_one_or_none()
    if user:
        return user
    raise HTTPException(status_code=500, detail="No dev user found. Seed the database first.")


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(HTTPBearer(auto_error=False))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    # DEV MODE — skip all auth, return first admin user
    if settings.DEV_MODE:
        return await _get_dev_user(db)

    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    clerk_user_id: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None

    try:
        if settings.CLERK_JWT_ISSUER:
            jwks_data = await _get_jwks()
            signing_key = _get_signing_key(jwks_data, token)

            if signing_key:
                payload = jwt.decode(
                    token,
                    key=signing_key,
                    algorithms=["RS256"],
                    options={"verify_aud": False},
                    issuer=settings.CLERK_JWT_ISSUER,
                )
            else:
                logger.warning("No matching signing key found in JWKS")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid authentication token",
                )
        else:
            payload = jwt.decode(
                token,
                key="dev-secret",
                algorithms=["HS256"],
                options={"verify_aud": False, "verify_iss": False, "verify_exp": False, "verify_signature": False},
            )

        clerk_user_id = payload.get("sub")
        email = payload.get("email", payload.get("email_address", ""))
        name = payload.get("name", payload.get("first_name", ""))

        if clerk_user_id is None:
            logger.warning("JWT missing 'sub' claim")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
    except JWTError as e:
        logger.warning("JWT decode failed: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
        )

    # Look up user by Clerk ID
    result = await db.execute(
        select(User).where(
            User.supabase_user_id == clerk_user_id,
            User.is_active.is_(True),
        )
    )
    user = result.scalar_one_or_none()

    # Auto-provision if not found
    if user is None:
        user = await _auto_provision_user(db, clerk_user_id, email or "", name or "")

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_approved:
        logger.warning("Access denied — user not approved: user=%s email=%s", user.id, user.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account is pending approval. Please contact the admin team for access.",
        )

    logger.debug("Authenticated user=%s tenant=%s", user.id, user.tenant_id)
    return user


async def get_current_tenant(
    user: Annotated[User, Depends(get_current_user)],
) -> uuid.UUID:
    return user.tenant_id


def require_role(required_role: UserRole):
    async def role_checker(
        user: Annotated[User, Depends(get_current_user)],
    ) -> User:
        if user.role != required_role and user.role != UserRole.admin:
            logger.warning(
                "Role check failed: user=%s has role=%s, required=%s",
                user.id, user.role, required_role,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return role_checker


CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentTenantId = Annotated[uuid.UUID, Depends(get_current_tenant)]
