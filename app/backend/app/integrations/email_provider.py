"""
Pluggable Email Provider System
--------------------------------
A simple abstraction that lets you swap email providers by setting one env var.

Supported providers:
  - sendgrid  (SendGrid — api key required)
  - resend    (Resend — api key required)
  - ses       (Amazon SES — AWS credentials required)
  - smtp      (Any SMTP server — host, port, user, pass)
  - log       (Development — logs emails to console, sends nothing)

Usage:
  Set EMAIL_PROVIDER=resend and RESEND_API_KEY=re_xxx in your .env.
  The campaign executor will automatically use the configured provider.

Adding a new provider:
  1. Create a class that implements EmailProvider (see below)
  2. Register it in PROVIDER_REGISTRY at the bottom of this file
  3. Add the required env vars to config.py and .env.example
"""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import settings

logger = logging.getLogger("integrations.email_provider")


# ---------------------------------------------------------------------------
# Shared result type
# ---------------------------------------------------------------------------

@dataclass
class EmailResult:
    """Result of an email send attempt."""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Base class — implement this to add a new provider
# ---------------------------------------------------------------------------

class EmailProvider(ABC):
    """
    Base class for email providers.

    To add a new provider, subclass this and implement:
      - name: a short identifier (e.g. "mailgun")
      - is_configured: return True when required env vars are set
      - send: deliver one email, return an EmailResult
      - close: clean up HTTP clients (optional)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this provider (e.g. 'sendgrid', 'resend')."""
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if the required API keys / credentials are present."""
        ...

    @abstractmethod
    async def send(
        self,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        reply_to: Optional[str] = None,
        tracking_id: Optional[str] = None,
    ) -> EmailResult:
        """Send a single email. Return EmailResult with success/message_id/error."""
        ...

    async def close(self) -> None:
        """Clean up resources (HTTP clients, connections). Called on shutdown."""
        pass


# ---------------------------------------------------------------------------
# Provider: SendGrid
# ---------------------------------------------------------------------------

class SendGridProvider(EmailProvider):
    """
    SendGrid (https://sendgrid.com)

    Required env vars:
      SENDGRID_API_KEY — your SendGrid API key

    Optional:
      SENDGRID_UNSUBSCRIBE_GROUP_ID — for CAN-SPAM unsubscribe links
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "sendgrid"

    @property
    def is_configured(self) -> bool:
        return bool(getattr(settings, "SENDGRID_API_KEY", ""))

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.sendgrid.com/v3",
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def send(
        self,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        reply_to: Optional[str] = None,
        tracking_id: Optional[str] = None,
    ) -> EmailResult:
        try:
            client = await self._get_client()
            payload: dict = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": from_email, "name": from_name},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_body}],
                "tracking_settings": {
                    "click_tracking": {"enable": True},
                    "open_tracking": {"enable": True},
                },
            }
            if reply_to:
                payload["reply_to"] = {"email": reply_to}
            if tracking_id:
                payload["custom_args"] = {"tracking_id": tracking_id}

            response = await client.post("/mail/send", json=payload)

            if response.status_code in (200, 202):
                msg_id = response.headers.get("X-Message-Id", "")
                return EmailResult(success=True, message_id=msg_id)
            else:
                return EmailResult(success=False, error=response.text[:500])

        except Exception as e:
            return EmailResult(success=False, error=str(e))

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


# ---------------------------------------------------------------------------
# Provider: Resend
# ---------------------------------------------------------------------------

class ResendProvider(EmailProvider):
    """
    Resend (https://resend.com)

    Required env vars:
      RESEND_API_KEY — your Resend API key (starts with re_)
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "resend"

    @property
    def is_configured(self) -> bool:
        return bool(getattr(settings, "RESEND_API_KEY", ""))

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url="https://api.resend.com",
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def send(
        self,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        reply_to: Optional[str] = None,
        tracking_id: Optional[str] = None,
    ) -> EmailResult:
        try:
            client = await self._get_client()
            payload: dict = {
                "from": f"{from_name} <{from_email}>",
                "to": [to_email],
                "subject": subject,
                "html": html_body,
            }
            if reply_to:
                payload["reply_to"] = reply_to
            if tracking_id:
                payload["headers"] = {"X-Tracking-Id": tracking_id}

            response = await client.post("/emails", json=payload)
            data = response.json()

            if response.status_code == 200 and data.get("id"):
                return EmailResult(success=True, message_id=data["id"])
            else:
                error = data.get("message") or data.get("error") or response.text[:500]
                return EmailResult(success=False, error=error)

        except Exception as e:
            return EmailResult(success=False, error=str(e))

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


# ---------------------------------------------------------------------------
# Provider: Amazon SES
# ---------------------------------------------------------------------------

class AmazonSESProvider(EmailProvider):
    """
    Amazon Simple Email Service (https://aws.amazon.com/ses/)

    Required env vars:
      AWS_ACCESS_KEY_ID     — your AWS access key
      AWS_SECRET_ACCESS_KEY — your AWS secret key
      AWS_SES_REGION        — AWS region (default: us-east-1)

    Note: Uses the SES v2 HTTP API directly (no boto3 dependency required).
    For production, consider using boto3 for proper AWS signature handling.
    This implementation uses the simpler SMTP interface instead.
    """

    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def name(self) -> str:
        return "ses"

    @property
    def is_configured(self) -> bool:
        return bool(
            getattr(settings, "AWS_ACCESS_KEY_ID", "")
            and getattr(settings, "AWS_SECRET_ACCESS_KEY", "")
        )

    async def send(
        self,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        reply_to: Optional[str] = None,
        tracking_id: Optional[str] = None,
    ) -> EmailResult:
        """Send via SES using SMTP (simpler than SigV4 signing)."""
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        region = getattr(settings, "AWS_SES_REGION", "us-east-1")
        smtp_host = f"email-smtp.{region}.amazonaws.com"

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = to_email
            if reply_to:
                msg["Reply-To"] = reply_to
            if tracking_id:
                msg["X-SES-CONFIGURATION-SET"] = "default"
                msg["X-Tracking-Id"] = tracking_id

            msg.attach(MIMEText(html_body, "html"))

            with smtplib.SMTP_SSL(smtp_host, 465) as server:
                server.login(
                    settings.AWS_ACCESS_KEY_ID,
                    settings.AWS_SECRET_ACCESS_KEY,
                )
                server.sendmail(from_email, [to_email], msg.as_string())

            return EmailResult(success=True, message_id=f"ses_{to_email}")

        except Exception as e:
            return EmailResult(success=False, error=str(e))


# ---------------------------------------------------------------------------
# Provider: Generic SMTP
# ---------------------------------------------------------------------------

class SMTPProvider(EmailProvider):
    """
    Generic SMTP provider — works with any SMTP server.

    Required env vars:
      SMTP_HOST     — SMTP server hostname (e.g. smtp.gmail.com)
      SMTP_PORT     — SMTP port (default: 587)
      SMTP_USER     — SMTP username
      SMTP_PASSWORD — SMTP password
      SMTP_USE_TLS  — "true" to use STARTTLS (default: true)
    """

    @property
    def name(self) -> str:
        return "smtp"

    @property
    def is_configured(self) -> bool:
        return bool(
            getattr(settings, "SMTP_HOST", "")
            and getattr(settings, "SMTP_USER", "")
        )

    async def send(
        self,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        reply_to: Optional[str] = None,
        tracking_id: Optional[str] = None,
    ) -> EmailResult:
        import smtplib
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{from_name} <{from_email}>"
            msg["To"] = to_email
            if reply_to:
                msg["Reply-To"] = reply_to

            msg.attach(MIMEText(html_body, "html"))

            host = settings.SMTP_HOST
            port = int(getattr(settings, "SMTP_PORT", "587"))
            use_tls = getattr(settings, "SMTP_USE_TLS", "true").lower() == "true"

            with smtplib.SMTP(host, port) as server:
                if use_tls:
                    server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(from_email, [to_email], msg.as_string())

            return EmailResult(success=True, message_id=f"smtp_{to_email}")

        except Exception as e:
            return EmailResult(success=False, error=str(e))


# ---------------------------------------------------------------------------
# Provider: Log (development / testing)
# ---------------------------------------------------------------------------

class LogProvider(EmailProvider):
    """
    Development provider — logs emails to console instead of sending them.
    Always returns success. Useful for local development and testing.
    """

    @property
    def name(self) -> str:
        return "log"

    @property
    def is_configured(self) -> bool:
        return True  # always available

    async def send(
        self,
        to_email: str,
        from_email: str,
        from_name: str,
        subject: str,
        html_body: str,
        reply_to: Optional[str] = None,
        tracking_id: Optional[str] = None,
    ) -> EmailResult:
        logger.info(
            "[LOG EMAIL] to=%s from=%s <%s> subject=%s body_len=%d",
            to_email, from_name, from_email, subject, len(html_body),
        )
        return EmailResult(success=True, message_id=f"log_{to_email}")


# ---------------------------------------------------------------------------
# Provider registry and factory
# ---------------------------------------------------------------------------

PROVIDER_REGISTRY: dict[str, type[EmailProvider]] = {
    "sendgrid": SendGridProvider,
    "resend": ResendProvider,
    "ses": AmazonSESProvider,
    "smtp": SMTPProvider,
    "log": LogProvider,
}

# Singleton instance — initialized on first use
_active_provider: Optional[EmailProvider] = None


def get_email_provider() -> EmailProvider:
    """
    Get the active email provider based on EMAIL_PROVIDER env var.

    Falls back to 'log' if no provider is configured or the configured
    provider is missing its required credentials.
    """
    global _active_provider
    if _active_provider is not None:
        return _active_provider

    provider_name = getattr(settings, "EMAIL_PROVIDER", "log").lower()

    if provider_name not in PROVIDER_REGISTRY:
        logger.warning(
            "Unknown EMAIL_PROVIDER=%r, falling back to 'log'. Available: %s",
            provider_name, ", ".join(PROVIDER_REGISTRY.keys()),
        )
        provider_name = "log"

    provider_class = PROVIDER_REGISTRY[provider_name]
    provider = provider_class()

    if not provider.is_configured:
        logger.warning(
            "EMAIL_PROVIDER=%r is not configured (missing credentials). "
            "Falling back to 'log' provider. Check your .env file.",
            provider_name,
        )
        provider = LogProvider()

    logger.info("Email provider initialized: %s", provider.name)
    _active_provider = provider
    return provider


def reset_email_provider() -> None:
    """Reset the provider singleton (useful for testing or reconfiguration)."""
    global _active_provider
    _active_provider = None
