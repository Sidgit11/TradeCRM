"""SendGrid email sending service.

Handles sending, warmup scheduling, and webhook parsing.
Currently uses mock responses; wire up real SendGrid API when credentials are available.
"""
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

import httpx

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("integrations.sendgrid")

SENDGRID_BASE_URL = "https://api.sendgrid.com/v3"

# Warmup schedule: day -> max emails per day
WARMUP_SCHEDULE = [20, 30, 50, 75, 100, 150, 200, 300, 500, 750, 1000]


@dataclass
class EmailSendResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class SendGridService:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.SENDGRID_API_KEY
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=SENDGRID_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def send_email(
        self,
        to_email: str,
        from_name: str,
        from_email: str,
        subject: str,
        html_body: str,
        tracking_id: Optional[str] = None,
    ) -> EmailSendResult:
        """Send a single email via SendGrid."""
        if not self.is_configured:
            logger.warning("SendGrid not configured, returning mock response")
            return EmailSendResult(success=True, message_id=f"mock_sg_{to_email}")

        logger.info("Sending email: to=%s subject=%s", to_email, subject[:50])

        try:
            client = await self._get_client()
            payload = {
                "personalizations": [{"to": [{"email": to_email}]}],
                "from": {"email": from_email, "name": from_name},
                "subject": subject,
                "content": [{"type": "text/html", "value": html_body}],
                "tracking_settings": {
                    "click_tracking": {"enable": True},
                    "open_tracking": {"enable": True},
                },
            }

            if tracking_id:
                payload["custom_args"] = {"tracking_id": tracking_id}

            # Add unsubscribe link (CAN-SPAM compliance)
            payload["content"][0]["value"] += (
                '\n<p style="font-size:11px;color:#999;margin-top:24px;">'
                'If you no longer wish to receive these emails, '
                '<a href="<%asm_group_unsubscribe_raw_url%>">unsubscribe</a>.</p>'
            )

            response = await client.post("/mail/send", json=payload)

            if response.status_code in (200, 202):
                msg_id = response.headers.get("X-Message-Id", "")
                logger.info("Email sent: to=%s msg_id=%s", to_email, msg_id)
                return EmailSendResult(success=True, message_id=msg_id)
            else:
                error = response.text
                logger.error("SendGrid error: to=%s status=%d error=%s", to_email, response.status_code, error)
                return EmailSendResult(success=False, error=error)

        except httpx.HTTPError as e:
            logger.error("SendGrid API error: %s", str(e))
            return EmailSendResult(success=False, error=str(e))

    def get_warmup_limit(self, warmup_day: int) -> int:
        """Get the max emails per day based on warmup schedule day number."""
        if warmup_day < 0:
            return WARMUP_SCHEDULE[0]
        if warmup_day >= len(WARMUP_SCHEDULE):
            return WARMUP_SCHEDULE[-1]
        return WARMUP_SCHEDULE[warmup_day]

    async def send_with_warmup(
        self,
        tenant_warmup_day: int,
        tenant_sent_today: int,
        to_email: str,
        from_name: str,
        from_email: str,
        subject: str,
        html_body: str,
        tracking_id: Optional[str] = None,
    ) -> EmailSendResult:
        """Send email respecting warmup schedule. Returns error if limit reached."""
        limit = self.get_warmup_limit(tenant_warmup_day)
        if tenant_sent_today >= limit:
            logger.warning(
                "Warmup limit reached: day=%d limit=%d sent=%d",
                tenant_warmup_day, limit, tenant_sent_today,
            )
            return EmailSendResult(
                success=False,
                error=f"Daily warmup limit reached ({limit} emails/day on day {tenant_warmup_day})",
            )

        return await self.send_email(to_email, from_name, from_email, subject, html_body, tracking_id)

    async def parse_webhook(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Parse SendGrid webhook events into normalized format."""
        parsed = []
        for event in events:
            parsed.append({
                "event_type": event.get("event", ""),
                "message_id": event.get("sg_message_id", "").split(".")[0] if event.get("sg_message_id") else "",
                "email": event.get("email", ""),
                "timestamp": event.get("timestamp", ""),
                "tracking_id": event.get("tracking_id", ""),
                "raw": event,
            })
        return parsed

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


sendgrid_service = SendGridService()
