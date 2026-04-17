"""Gupshup Direct API — sends messages using HSM and Two-way accounts.

Uses the direct messaging API (not Partner API) for sending from your own WABA number.
HSM = Template messages (outside 24hr window)
Two-way = Session messages (within 24hr window)
"""
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings
from app.logging_config import get_logger

logger = get_logger("integrations.gupshup_direct")

# Gupshup Enterprise API endpoints
HSM_API = "https://media.smsgupshup.com/GatewayAPI/rest"
TWOWAY_API = "https://media.smsgupshup.com/GatewayAPI/rest"


@dataclass
class SendResult:
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class GupshupDirectService:
    """Direct Gupshup messaging using HSM and Two-way accounts."""

    @property
    def is_configured(self) -> bool:
        return bool(settings.GUPSHUP_HSM_USERID and settings.GUPSHUP_WABA_NUMBER)

    @property
    def waba_number(self) -> str:
        return settings.GUPSHUP_WABA_NUMBER

    async def send_hsm_message(
        self,
        destination: str,
        template_name: str,
        namespace: str,
        params: List[str],
        language: str = "en",
    ) -> SendResult:
        """Send a template (HSM) message. Used for campaigns and first-touch."""
        if not self.is_configured:
            logger.warning("gupshup_direct: HSM not configured, returning mock")
            return SendResult(success=True, message_id=f"mock_hsm_{destination}")

        logger.info("gupshup_direct: sending HSM | to=%s template=%s params=%s", destination, template_name, params)

        # Build template payload
        template_payload = json.dumps({
            "id": template_name,
            "params": params,
        })

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    HSM_API,
                    data={
                        "method": "SendMessage",
                        "userid": settings.GUPSHUP_HSM_USERID,
                        "password": settings.GUPSHUP_HSM_PASSWORD,
                        "send_to": destination,
                        "v": "1.1",
                        "format": "json",
                        "msg_type": "HSM",
                        "isHSM": "true",
                        "isTemplate": "true",
                    },
                )

                if response.status_code == 200:
                    data = response.json() if "json" in response.headers.get("content-type", "") else {}
                    resp = data.get("response", data)
                    msg_id = resp.get("id", "")
                    success = resp.get("status", "").lower() == "success"
                    logger.info("gupshup_direct: HSM sent | to=%s success=%s msg_id=%s", destination, success, msg_id)
                    return SendResult(success=success, message_id=str(msg_id) if msg_id else None)
                else:
                    logger.error("gupshup_direct: HSM failed | to=%s status=%d error=%s", destination, response.status_code, response.text[:200])
                    return SendResult(success=False, error=response.text[:200])

        except Exception as e:
            logger.error("gupshup_direct: HSM error | to=%s error=%s", destination, str(e))
            return SendResult(success=False, error=str(e))

    async def send_session_message(
        self,
        destination: str,
        text: str,
    ) -> SendResult:
        """Send a free-form session message (within 24hr window)."""
        if not self.is_configured:
            logger.warning("gupshup_direct: Two-way not configured, returning mock")
            return SendResult(success=True, message_id=f"mock_twoway_{destination}")

        logger.info("gupshup_direct: sending session msg | to=%s len=%d", destination, len(text))

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    TWOWAY_API,
                    data={
                        "method": "SendMessage",
                        "userid": settings.GUPSHUP_TWOWAY_USERID,
                        "password": settings.GUPSHUP_TWOWAY_PASSWORD,
                        "send_to": destination,
                        "v": "1.1",
                        "format": "json",
                        "msg_type": "TEXT",
                        "msg": text,
                    },
                )

                data = response.json() if "json" in response.headers.get("content-type", "") else {}
                resp = data.get("response", data)
                msg_id = resp.get("id", "")
                success = resp.get("status", "").lower() == "success"
                logger.info("gupshup_direct: session msg | to=%s success=%s msg_id=%s", destination, success, msg_id)
                return SendResult(success=success, message_id=str(msg_id) if msg_id else None, error=None if success else response.text[:200])

        except Exception as e:
            logger.error("gupshup_direct: session msg error | to=%s error=%s", destination, str(e))
            return SendResult(success=False, error=str(e))

    async def check_opt_in(self, phone: str) -> bool:
        """Check if a number is opted-in for messaging."""
        # For now, assume opted-in. In production, check via Gupshup API.
        return True

    async def send_opt_in_request(self, phone: str) -> bool:
        """Send opt-in request to a phone number."""
        logger.info("gupshup_direct: opt-in request | phone=%s (placeholder)", phone)
        return True


# Singleton
gupshup_direct = GupshupDirectService()
