"""Gupshup WhatsApp Partner API integration.

Real implementation using Partner API for multi-tenant WhatsApp.
Each tenant gets their own Gupshup App with their own phone number.
"""
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("integrations.gupshup")

PARTNER_API = "https://partner.gupshup.io/partner"
MESSAGING_API = "https://api.gupshup.io/wa/api/v1"


@dataclass
class SendResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class GupshupPartnerService:
    """Manages all Gupshup Partner API interactions for multi-tenant WhatsApp."""

    def __init__(self):
        self._partner_token: Optional[str] = None
        self._token_expires_at: float = 0
        self._app_tokens: Dict[str, tuple] = {}  # app_id -> (token, expires_at)

    @property
    def is_configured(self) -> bool:
        return bool(settings.GUPSHUP_PARTNER_EMAIL and settings.GUPSHUP_PARTNER_SECRET)

    # --- Authentication ---

    async def get_partner_token(self) -> str:
        """Get cached partner token, refresh if expired (24hr validity)."""
        if self._partner_token and time.time() < self._token_expires_at:
            return self._partner_token

        logger.info("gupshup: fetching partner token")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{PARTNER_API}/account/login",
                data={
                    "email": settings.GUPSHUP_PARTNER_EMAIL,
                    "password": settings.GUPSHUP_PARTNER_SECRET,
                },
                headers={"Accept": "application/json"},
            )

            if response.status_code != 200:
                logger.error("gupshup: partner login failed %d: %s", response.status_code, response.text[:200])
                raise Exception(f"Gupshup partner login failed: {response.status_code}")

            data = response.json()
            self._partner_token = data.get("token", "")
            self._token_expires_at = time.time() + 23 * 3600  # refresh 1hr before 24hr expiry
            logger.info("gupshup: partner token obtained")
            return self._partner_token

    async def get_app_token(self, app_id: str) -> str:
        """Get app-level API key for a customer's app."""
        cached = self._app_tokens.get(app_id)
        if cached and time.time() < cached[1]:
            return cached[0]

        token = await self.get_partner_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{PARTNER_API}/app/{app_id}/token/",
                headers={"Authorization": token},
            )
            if response.status_code != 200:
                logger.error("gupshup: get app token failed for %s: %s", app_id, response.text[:200])
                raise Exception(f"Failed to get app token for {app_id}")

            data = response.json()
            app_token = data.get("token", {}).get("token", "") if isinstance(data.get("token"), dict) else data.get("token", "")
            self._app_tokens[app_id] = (app_token, time.time() + 23 * 3600)
            logger.info("gupshup: app token obtained for %s", app_id)
            return app_token

    # --- Customer Onboarding ---

    async def create_app(self, app_name: str) -> Dict[str, str]:
        """Create a new Gupshup App for a customer tenant."""
        token = await self.get_partner_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{PARTNER_API}/app",
                json={"name": app_name},
                headers={"Authorization": token, "Content-Type": "application/json"},
            )
            if response.status_code not in (200, 201):
                logger.error("gupshup: create app failed: %s", response.text[:200])
                raise Exception(f"Failed to create app: {response.text[:200]}")

            data = response.json()
            logger.info("gupshup: app created | name=%s id=%s", app_name, data.get("appId"))
            return {"app_id": data.get("appId", ""), "app_name": app_name}

    async def set_callback_url(self, app_id: str, callback_url: str) -> Dict:
        """Set webhook callback URL for a customer's app."""
        token = await self.get_partner_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.put(
                f"{PARTNER_API}/app/{app_id}/callback",
                json={"url": callback_url},
                headers={"Authorization": token, "Content-Type": "application/json"},
            )
            logger.info("gupshup: callback URL set for %s: %s -> %d", app_id, callback_url, response.status_code)
            return response.json() if response.status_code == 200 else {"error": response.text[:200]}

    async def generate_embed_link(self, app_id: str, user_email: str) -> str:
        """Generate Embedded Signup URL for customer WhatsApp onboarding."""
        token = await self.get_partner_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{PARTNER_API}/app/{app_id}/onboarding/embed/link",
                params={"regenerate": "false", "user": user_email, "lang": "en"},
                headers={"Authorization": token},
            )
            if response.status_code != 200:
                logger.error("gupshup: embed link failed: %s", response.text[:200])
                raise Exception("Failed to generate embed link")

            data = response.json()
            url = data.get("url", data.get("embedUrl", ""))
            logger.info("gupshup: embed link generated for %s", app_id)
            return url

    async def whitelist_waba(self, app_id: str) -> Dict:
        """Whitelist WABA after customer completes Embedded Signup."""
        token = await self.get_partner_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{PARTNER_API}/app/{app_id}/obotoembed/whitelist",
                headers={"Authorization": token},
            )
            logger.info("gupshup: WABA whitelisted for %s: %d", app_id, response.status_code)
            return response.json() if response.status_code == 200 else {"error": response.text[:200]}

    async def verify_and_attach_credit(self, app_id: str) -> Dict:
        """Verify WABA and attach credit line."""
        token = await self.get_partner_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{PARTNER_API}/app/{app_id}/obotoembed/verify",
                headers={"Authorization": token},
            )
            logger.info("gupshup: verify+credit for %s: %d", app_id, response.status_code)
            return response.json() if response.status_code == 200 else {"error": response.text[:200]}

    async def get_app_details(self, app_id: str) -> Dict:
        """Get full app details including phone number and status."""
        token = await self.get_partner_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{PARTNER_API}/app/{app_id}",
                headers={"Authorization": token},
            )
            if response.status_code != 200:
                return {"error": response.text[:200]}
            return response.json()

    # --- Messaging ---

    async def send_template_message(
        self, app_id: str, app_name: str, source_phone: str,
        destination_phone: str, template_id: str, params: List[str],
    ) -> SendResult:
        """Send a template (HSM) message. Used for campaigns and outside 24hr window."""
        app_token = await self.get_app_token(app_id)

        async with httpx.AsyncClient(timeout=30) as client:
            import json
            response = await client.post(
                f"{MESSAGING_API}/template/msg",
                data={
                    "channel": "whatsapp",
                    "source": source_phone,
                    "destination": destination_phone,
                    "src.name": app_name,
                    "template": json.dumps({"id": template_id, "params": params}),
                },
                headers={"apikey": app_token},
            )

            if response.status_code == 200:
                data = response.json()
                msg_id = data.get("messageId", "")
                logger.info("gupshup: template msg sent | to=%s msg=%s", destination_phone, msg_id)
                return SendResult(success=True, message_id=msg_id)
            else:
                logger.error("gupshup: template msg failed | to=%s status=%d error=%s",
                    destination_phone, response.status_code, response.text[:200])
                return SendResult(success=False, error=response.text[:200])

    async def send_session_message(
        self, app_id: str, app_name: str, source_phone: str,
        destination_phone: str, text: str,
    ) -> SendResult:
        """Send a session (free-form) message. Only within 24hr window."""
        app_token = await self.get_app_token(app_id)

        async with httpx.AsyncClient(timeout=30) as client:
            import json
            response = await client.post(
                f"{MESSAGING_API}/msg",
                data={
                    "channel": "whatsapp",
                    "source": source_phone,
                    "destination": destination_phone,
                    "src.name": app_name,
                    "message": json.dumps({"type": "text", "text": text}),
                },
                headers={"apikey": app_token},
            )

            if response.status_code == 200 or response.status_code == 202:
                data = response.json()
                msg_id = data.get("messageId", "")
                logger.info("gupshup: session msg sent | to=%s msg=%s", destination_phone, msg_id)
                return SendResult(success=True, message_id=msg_id)
            else:
                logger.error("gupshup: session msg failed | to=%s error=%s", destination_phone, response.text[:200])
                return SendResult(success=False, error=response.text[:200])

    # --- Template Management ---

    async def get_templates(self, app_id: str) -> List[Dict]:
        """List all templates for a customer's app."""
        token = await self.get_partner_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{PARTNER_API}/app/{app_id}/templates",
                headers={"Authorization": token},
            )
            if response.status_code != 200:
                logger.error("gupshup: get templates failed for %s", app_id)
                return []
            data = response.json()
            templates = data.get("templates", data) if isinstance(data, dict) else data
            return templates if isinstance(templates, list) else []

    async def create_template(
        self, app_id: str, name: str, category: str,
        language: str, content: str, example: str,
    ) -> Dict:
        """Submit a new template for Meta approval."""
        token = await self.get_partner_token()
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{PARTNER_API}/app/{app_id}/templates",
                json={
                    "elementName": name,
                    "category": category,
                    "languageCode": language,
                    "content": content,
                    "example": example,
                    "templateType": "TEXT",
                    "vertical": "MARKETING",
                },
                headers={"Authorization": token, "Content-Type": "application/json"},
            )
            logger.info("gupshup: template submitted | app=%s name=%s status=%d", app_id, name, response.status_code)
            return response.json() if response.status_code in (200, 201) else {"error": response.text[:200]}

    # --- Webhook Parsing ---

    async def parse_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parse incoming Gupshup webhook into normalized event."""
        event_type = payload.get("type", "")
        app_name = payload.get("app", "")

        if event_type == "message":
            msg_payload = payload.get("payload", {})
            return {
                "kind": "inbound_message",
                "app_name": app_name,
                "phone": msg_payload.get("source", ""),
                "text": msg_payload.get("payload", {}).get("text", ""),
                "message_type": msg_payload.get("type", "text"),
                "message_id": msg_payload.get("id", ""),
                "timestamp": payload.get("timestamp", ""),
                "raw": payload,
            }
        elif event_type == "message-event":
            evt_payload = payload.get("payload", {})
            return {
                "kind": "status_update",
                "app_name": app_name,
                "message_id": evt_payload.get("id", ""),
                "status": evt_payload.get("type", ""),
                "phone": evt_payload.get("destination", ""),
                "gswa_id": evt_payload.get("gsId", ""),
                "error_reason": evt_payload.get("payload", {}).get("reason", "") if isinstance(evt_payload.get("payload"), dict) else "",
                "timestamp": payload.get("timestamp", ""),
                "raw": payload,
            }
        elif event_type == "template-event":
            return {
                "kind": "template_status",
                "app_name": app_name,
                "template_name": payload.get("payload", {}).get("elementName", ""),
                "status": payload.get("payload", {}).get("status", ""),
                "reason": payload.get("payload", {}).get("reason", ""),
                "raw": payload,
            }
        elif event_type == "account-event":
            return {
                "kind": "account_status",
                "app_name": app_name,
                "status": payload.get("payload", {}).get("status", ""),
                "raw": payload,
            }

        return {"kind": "unknown", "app_name": app_name, "raw": payload}


# Singleton
gupshup_service = GupshupPartnerService()
