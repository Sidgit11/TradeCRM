"""Email API — Gmail OAuth connect, inbox reading, send, reply, labels."""
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.logging_config import get_logger
from app.middleware.tenant import CurrentTenantId, CurrentUser
from app.models.email_account import EmailAccount
from app.integrations import gmail_service

logger = get_logger("api.email")
router = APIRouter(prefix="/email", tags=["email"])


# --- Schemas ---

class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body_html: str
    cc: Optional[str] = None
    bcc: Optional[str] = None


class ReplyEmailRequest(BaseModel):
    message_id: str
    body_html: str


class DraftEmailRequest(BaseModel):
    to: str
    subject: str
    body_html: str
    thread_id: Optional[str] = None


class ModifyLabelsRequest(BaseModel):
    add_labels: Optional[List[str]] = None
    remove_labels: Optional[List[str]] = None


# --- Helpers ---

async def _get_account(
    db: AsyncSession, tenant_id: uuid.UUID, account_id: uuid.UUID
) -> EmailAccount:
    result = await db.execute(
        select(EmailAccount).where(
            EmailAccount.id == account_id,
            EmailAccount.tenant_id == tenant_id,
            EmailAccount.is_active.is_(True),
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Email account not found")
    if not account.token_data:
        raise HTTPException(status_code=400, detail="Email account not connected")
    return account


async def _save_updated_tokens(db: AsyncSession, account: EmailAccount, result: Dict[str, Any]):
    """Persist refreshed tokens back to DB."""
    updated = result.get("updated_tokens")
    if updated and updated.get("access_token") != (account.token_data or {}).get("access_token"):
        account.token_data = updated
        await db.commit()


# --- OAuth Flow ---

@router.get("/connect/gmail")
async def start_gmail_oauth(
    tenant_id: CurrentTenantId,
    user: CurrentUser,
):
    """Start Gmail OAuth flow. Redirects user to Google consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")

    try:
        state = f"{tenant_id}:{user.id}"
        auth_url = gmail_service.get_auth_url(state=state)
        logger.info("Gmail OAuth started: tenant=%s user=%s", tenant_id, user.id)
        return {"auth_url": auth_url}
    except Exception as e:
        logger.error("Gmail OAuth start failed: tenant=%s error=%s", tenant_id, str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to start Gmail authorization. Please try again.")


@router.get("/callback/gmail")
async def gmail_oauth_callback(
    code: str,
    state: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth callback. Exchanges code for tokens and saves the account."""
    if not code:
        raise HTTPException(status_code=400, detail="Missing authorization code")

    # Parse state
    parts = state.split(":")
    tenant_id_str = parts[0] if len(parts) > 0 else ""
    user_id_str = parts[1] if len(parts) > 1 else ""

    try:
        tenant_id = uuid.UUID(tenant_id_str)
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state parameter")

    # Exchange code for tokens
    try:
        tokens = gmail_service.exchange_code_for_tokens(code, state=state)
    except Exception as e:
        logger.error("Gmail OAuth token exchange failed: error=%s", str(e), exc_info=True)
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings/integrations?gmail=error&reason=token_exchange_failed")

    # Get profile to find the email address
    try:
        profile = gmail_service.get_profile(tokens)
        email_address = profile["email"]
    except Exception as e:
        logger.error("Gmail profile fetch failed: error=%s", str(e), exc_info=True)
        return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings/integrations?gmail=error&reason=profile_fetch_failed")

    # Check if this email is already connected for this tenant
    existing = await db.execute(
        select(EmailAccount).where(
            EmailAccount.tenant_id == tenant_id,
            EmailAccount.email_address == email_address,
        )
    )
    account = existing.scalar_one_or_none()

    if account:
        account.token_data = tokens
        account.is_active = True
    else:
        account = EmailAccount(
            tenant_id=tenant_id,
            email_address=email_address,
            provider="gmail",
            display_name=email_address,
            token_data=tokens,
            connected_by=user_id,
        )
        db.add(account)

    await db.commit()
    logger.info("Gmail connected: email=%s tenant=%s", email_address, tenant_id)

    return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings/integrations?gmail=connected&email={email_address}")


# --- Account Management ---

@router.get("/accounts")
async def list_email_accounts(
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """List all connected email accounts for the tenant."""
    result = await db.execute(
        select(EmailAccount).where(
            EmailAccount.tenant_id == tenant_id,
            EmailAccount.is_active.is_(True),
        )
    )
    return [
        {
            "id": str(a.id),
            "email_address": a.email_address,
            "provider": a.provider,
            "display_name": a.display_name,
            "is_active": a.is_active,
            "last_sync_at": a.last_sync_at,
            "created_at": a.created_at.isoformat(),
        }
        for a in result.scalars().all()
    ]


@router.delete("/accounts/{account_id}", status_code=204)
async def disconnect_email_account(
    account_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Disconnect an email account (soft-deactivate)."""
    account = await _get_account(db, tenant_id, account_id)
    account.is_active = False
    account.token_data = None
    await db.commit()
    logger.info("Email account disconnected: %s tenant=%s", account.email_address, tenant_id)


# --- Inbox ---

@router.get("/accounts/{account_id}/messages")
async def list_account_messages(
    account_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
    q: str = "",
    max_results: int = Query(20, ge=1, le=100),
    page_token: Optional[str] = None,
    label: Optional[str] = None,
):
    """List messages from a connected email account. Default: last 7 days."""
    account = await _get_account(db, tenant_id, account_id)
    label_ids = [label] if label else None

    # Default to last 7 days if no query specified
    if not q:
        q = "newer_than:7d"
    elif "newer_than:" not in q and "after:" not in q:
        q = f"newer_than:7d {q}"

    result = gmail_service.list_messages(
        account.token_data, query=q, max_results=max_results,
        label_ids=label_ids, page_token=page_token,
    )
    await _save_updated_tokens(db, account, result)
    return result


@router.get("/accounts/{account_id}/messages/{message_id}")
async def get_account_message(
    account_id: uuid.UUID,
    message_id: str,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get full message details."""
    account = await _get_account(db, tenant_id, account_id)
    result = gmail_service.get_message(account.token_data, message_id)
    await _save_updated_tokens(db, account, result)
    return result


@router.get("/accounts/{account_id}/threads/{thread_id}")
async def get_account_thread(
    account_id: uuid.UUID,
    thread_id: str,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get all messages in a thread."""
    account = await _get_account(db, tenant_id, account_id)
    result = gmail_service.get_thread(account.token_data, thread_id)
    await _save_updated_tokens(db, account, result)
    return result


# --- Send & Reply ---

@router.post("/accounts/{account_id}/send")
async def send_from_account(
    account_id: uuid.UUID,
    body: SendEmailRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Send an email from a connected account."""
    account = await _get_account(db, tenant_id, account_id)
    result = gmail_service.send_email(
        account.token_data, to=body.to, subject=body.subject,
        body_html=body.body_html, cc=body.cc, bcc=body.bcc,
    )
    await _save_updated_tokens(db, account, result)
    logger.info("Email sent from %s to %s", account.email_address, body.to)
    return result


@router.post("/accounts/{account_id}/reply")
async def reply_from_account(
    account_id: uuid.UUID,
    body: ReplyEmailRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Reply to a message from a connected account."""
    account = await _get_account(db, tenant_id, account_id)
    # Fetch original message for threading
    original = gmail_service.get_message(account.token_data, body.message_id)
    result = gmail_service.reply_to_message(account.token_data, original, body.body_html)
    await _save_updated_tokens(db, account, result)
    logger.info("Reply sent from %s to %s", account.email_address, original.get("from", ""))
    return result


# --- Drafts ---

@router.post("/accounts/{account_id}/drafts")
async def create_account_draft(
    account_id: uuid.UUID,
    body: DraftEmailRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Create a draft in a connected account."""
    account = await _get_account(db, tenant_id, account_id)
    result = gmail_service.create_draft(
        account.token_data, to=body.to, subject=body.subject,
        body_html=body.body_html, thread_id=body.thread_id,
    )
    await _save_updated_tokens(db, account, result)
    return result


# --- Labels ---

@router.get("/accounts/{account_id}/labels")
async def list_account_labels(
    account_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """List Gmail labels for a connected account."""
    account = await _get_account(db, tenant_id, account_id)
    return gmail_service.list_labels(account.token_data)


@router.post("/accounts/{account_id}/messages/{message_id}/labels")
async def modify_message_labels(
    account_id: uuid.UUID,
    message_id: str,
    body: ModifyLabelsRequest,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Modify labels on a message (mark read, archive, etc.)."""
    account = await _get_account(db, tenant_id, account_id)
    return gmail_service.modify_labels(
        account.token_data, message_id,
        add_labels=body.add_labels, remove_labels=body.remove_labels,
    )


@router.post("/accounts/{account_id}/messages/{message_id}/read")
async def mark_message_read(
    account_id: uuid.UUID,
    message_id: str,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Mark a message as read."""
    account = await _get_account(db, tenant_id, account_id)
    return gmail_service.mark_as_read(account.token_data, message_id)


@router.post("/accounts/{account_id}/messages/{message_id}/archive")
async def archive_account_message(
    account_id: uuid.UUID,
    message_id: str,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Archive a message."""
    account = await _get_account(db, tenant_id, account_id)
    return gmail_service.archive_message(account.token_data, message_id)


# --- Profile ---

@router.get("/accounts/{account_id}/profile")
async def get_account_profile(
    account_id: uuid.UUID,
    tenant_id: CurrentTenantId,
    db: AsyncSession = Depends(get_db),
):
    """Get profile info for a connected account."""
    account = await _get_account(db, tenant_id, account_id)
    result = gmail_service.get_profile(account.token_data)
    await _save_updated_tokens(db, account, result)
    return result
