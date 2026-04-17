"""Gmail OAuth integration — real Google API implementation.

Supports: OAuth flow, read inbox, search, send, reply, drafts, labels, attachments.
Handles multiple connected accounts per tenant.
"""
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("integrations.gmail")

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
    "https://mail.google.com/",
]


def _get_client_config() -> dict:
    return {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }


# Store pending OAuth flows (state → Flow) so code_verifier is preserved
_pending_flows: Dict[str, Flow] = {}


def get_auth_url(state: str) -> str:
    """Generate Google OAuth consent URL."""
    flow = Flow.from_client_config(_get_client_config(), scopes=SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )
    # Store flow so callback can use the same code_verifier
    _pending_flows[state] = flow
    logger.info("Gmail OAuth URL generated, state=%s", state)
    return auth_url


def exchange_code_for_tokens(code: str, state: str = "") -> Dict[str, str]:
    """Exchange authorization code for access + refresh tokens."""
    # Retrieve the original flow with code_verifier
    flow = _pending_flows.pop(state, None)
    if not flow:
        flow = Flow.from_client_config(_get_client_config(), scopes=SCOPES)
        flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    flow.fetch_token(code=code)
    creds = flow.credentials

    tokens = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token or "",
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "expiry": creds.expiry.isoformat() if creds.expiry else "",
    }
    logger.info("Gmail tokens exchanged successfully")
    return tokens


def _build_service(token_data: Dict[str, str]):
    """Build Gmail API service from stored token data."""
    creds = Credentials(
        token=token_data.get("access_token"),
        refresh_token=token_data.get("refresh_token"),
        token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
        client_id=token_data.get("client_id", settings.GOOGLE_CLIENT_ID),
        client_secret=token_data.get("client_secret", settings.GOOGLE_CLIENT_SECRET),
    )

    if creds.expired or not creds.valid:
        creds.refresh(GoogleRequest())
        token_data["access_token"] = creds.token
        if creds.expiry:
            token_data["expiry"] = creds.expiry.isoformat()
        logger.info("Gmail token refreshed")

    return build("gmail", "v1", credentials=creds), token_data


def get_profile(token_data: Dict[str, str]) -> Dict[str, Any]:
    """Get the connected Gmail account's email address and profile."""
    service, token_data = _build_service(token_data)
    profile = service.users().getProfile(userId="me").execute()
    return {
        "email": profile.get("emailAddress", ""),
        "messages_total": profile.get("messagesTotal", 0),
        "threads_total": profile.get("threadsTotal", 0),
        "history_id": profile.get("historyId", ""),
        "updated_tokens": token_data,
    }


def list_messages(
    token_data: Dict[str, str],
    query: str = "",
    max_results: int = 20,
    label_ids: Optional[List[str]] = None,
    page_token: Optional[str] = None,
) -> Dict[str, Any]:
    """List messages from Gmail inbox."""
    service, token_data = _build_service(token_data)

    kwargs: Dict[str, Any] = {"userId": "me", "maxResults": max_results}
    if query:
        kwargs["q"] = query
    if label_ids:
        kwargs["labelIds"] = label_ids
    if page_token:
        kwargs["pageToken"] = page_token

    result = service.users().messages().list(**kwargs).execute()
    messages = result.get("messages", [])

    logger.info("Listed %d messages, query='%s'", len(messages), query)
    return {
        "messages": [{"id": m["id"], "threadId": m["threadId"]} for m in messages],
        "next_page_token": result.get("nextPageToken"),
        "result_size_estimate": result.get("resultSizeEstimate", 0),
        "updated_tokens": token_data,
    }


def get_message(token_data: Dict[str, str], message_id: str) -> Dict[str, Any]:
    """Get full message details including headers, body, and attachments."""
    service, token_data = _build_service(token_data)
    msg = service.users().messages().get(userId="me", id=message_id, format="full").execute()

    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}

    body_text = ""
    body_html = ""
    attachments: List[Dict[str, Any]] = []

    def _extract_parts(payload: dict):
        nonlocal body_text, body_html
        mime_type = payload.get("mimeType", "")
        body_data = payload.get("body", {}).get("data")
        if mime_type == "text/plain" and body_data:
            body_text = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        elif mime_type == "text/html" and body_data:
            body_html = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="replace")
        elif payload.get("filename"):
            attachments.append({
                "filename": payload["filename"],
                "mime_type": mime_type,
                "size": payload.get("body", {}).get("size", 0),
                "attachment_id": payload.get("body", {}).get("attachmentId", ""),
            })
        for part in payload.get("parts", []):
            _extract_parts(part)

    _extract_parts(msg.get("payload", {}))

    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId", ""),
        "label_ids": msg.get("labelIds", []),
        "snippet": msg.get("snippet", ""),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "cc": headers.get("cc", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "message_id_header": headers.get("message-id", ""),
        "in_reply_to": headers.get("in-reply-to", ""),
        "references": headers.get("references", ""),
        "body_text": body_text,
        "body_html": body_html,
        "attachments": attachments,
        "size_estimate": msg.get("sizeEstimate", 0),
        "internal_date": msg.get("internalDate", ""),
        "updated_tokens": token_data,
    }


def get_thread(token_data: Dict[str, str], thread_id: str) -> Dict[str, Any]:
    """Get all messages in a thread."""
    service, token_data = _build_service(token_data)
    thread = service.users().threads().get(userId="me", id=thread_id, format="metadata").execute()
    messages = []
    for msg in thread.get("messages", []):
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        messages.append({
            "id": msg["id"],
            "snippet": msg.get("snippet", ""),
            "from": headers.get("from", ""),
            "to": headers.get("to", ""),
            "subject": headers.get("subject", ""),
            "date": headers.get("date", ""),
            "label_ids": msg.get("labelIds", []),
        })
    return {"id": thread["id"], "messages": messages, "updated_tokens": token_data}


def send_email(
    token_data: Dict[str, str],
    to: str,
    subject: str,
    body_html: str,
    cc: Optional[str] = None,
    bcc: Optional[str] = None,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Send an email from the connected Gmail account."""
    service, token_data = _build_service(token_data)

    message = MIMEMultipart("alternative")
    message["to"] = to
    message["subject"] = subject
    if cc:
        message["cc"] = cc
    if bcc:
        message["bcc"] = bcc
    if in_reply_to:
        message["In-Reply-To"] = in_reply_to
        message["References"] = references or in_reply_to

    message.attach(MIMEText(body_html, "html"))

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    body: Dict[str, Any] = {"raw": raw}
    if thread_id:
        body["threadId"] = thread_id

    sent = service.users().messages().send(userId="me", body=body).execute()
    logger.info("Email sent: to=%s msg_id=%s", to, sent.get("id", ""))
    return {"id": sent.get("id", ""), "thread_id": sent.get("threadId", ""), "updated_tokens": token_data}


def reply_to_message(
    token_data: Dict[str, str],
    original_message: Dict[str, Any],
    body_html: str,
) -> Dict[str, Any]:
    """Reply to an existing message, keeping it in the same thread."""
    subject = original_message.get("subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    return send_email(
        token_data=token_data,
        to=original_message.get("from", ""),
        subject=subject,
        body_html=body_html,
        in_reply_to=original_message.get("message_id_header", ""),
        references=original_message.get("references", original_message.get("message_id_header", "")),
        thread_id=original_message.get("thread_id", ""),
    )


def create_draft(
    token_data: Dict[str, str],
    to: str,
    subject: str,
    body_html: str,
    thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a draft email."""
    service, token_data = _build_service(token_data)
    message = MIMEMultipart("alternative")
    message["to"] = to
    message["subject"] = subject
    message.attach(MIMEText(body_html, "html"))
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
    body: Dict[str, Any] = {"message": {"raw": raw}}
    if thread_id:
        body["message"]["threadId"] = thread_id
    draft = service.users().drafts().create(userId="me", body=body).execute()
    logger.info("Draft created: id=%s", draft.get("id", ""))
    return {"draft_id": draft.get("id", ""), "updated_tokens": token_data}


def list_labels(token_data: Dict[str, str]) -> List[Dict[str, str]]:
    """List all Gmail labels."""
    service, token_data = _build_service(token_data)
    result = service.users().labels().list(userId="me").execute()
    return [{"id": l["id"], "name": l["name"], "type": l.get("type", "")} for l in result.get("labels", [])]


def modify_labels(
    token_data: Dict[str, str],
    message_id: str,
    add_labels: Optional[List[str]] = None,
    remove_labels: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Add or remove labels from a message."""
    service, token_data = _build_service(token_data)
    body: Dict[str, Any] = {}
    if add_labels:
        body["addLabelIds"] = add_labels
    if remove_labels:
        body["removeLabelIds"] = remove_labels
    result = service.users().messages().modify(userId="me", id=message_id, body=body).execute()
    return {"id": result.get("id", ""), "label_ids": result.get("labelIds", [])}


def mark_as_read(token_data: Dict[str, str], message_id: str) -> Dict[str, Any]:
    return modify_labels(token_data, message_id, remove_labels=["UNREAD"])


def archive_message(token_data: Dict[str, str], message_id: str) -> Dict[str, Any]:
    return modify_labels(token_data, message_id, remove_labels=["INBOX"])
