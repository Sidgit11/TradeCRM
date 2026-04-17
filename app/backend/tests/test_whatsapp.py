"""Tests for WhatsApp integration — Gupshup service, webhooks, 24hr window, security."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.integrations.gupshup import GupshupPartnerService

client = TestClient(app)


class TestGupshupService:
    def test_is_configured_check(self):
        service = GupshupPartnerService()
        from app.config import settings
        expected = bool(settings.GUPSHUP_PARTNER_EMAIL and settings.GUPSHUP_PARTNER_SECRET)
        assert service.is_configured == expected

    @pytest.mark.asyncio
    async def test_parse_inbound_message(self):
        service = GupshupPartnerService()
        event = await service.parse_webhook({
            "app": "tradecrm_test", "type": "message",
            "payload": {"source": "919876543210", "type": "text",
                        "payload": {"text": "Hi, interested in pepper"}, "id": "msg_1"},
        })
        assert event["kind"] == "inbound_message"
        assert event["phone"] == "919876543210"
        assert "pepper" in event["text"]

    @pytest.mark.asyncio
    async def test_parse_status_update(self):
        service = GupshupPartnerService()
        event = await service.parse_webhook({
            "app": "test", "type": "message-event",
            "payload": {"id": "msg_2", "type": "delivered", "destination": "919876543210"},
        })
        assert event["kind"] == "status_update"
        assert event["status"] == "delivered"

    @pytest.mark.asyncio
    async def test_parse_template_event(self):
        service = GupshupPartnerService()
        event = await service.parse_webhook({
            "app": "test", "type": "template-event",
            "payload": {"elementName": "buyer_intro", "status": "approved"},
        })
        assert event["kind"] == "template_status"
        assert event["template_name"] == "buyer_intro"

    @pytest.mark.asyncio
    async def test_parse_unknown_event(self):
        service = GupshupPartnerService()
        event = await service.parse_webhook({"type": "new_type", "app": "x"})
        assert event["kind"] == "unknown"


class TestWhatsAppWebhook:
    def test_webhook_accepts_template_event(self):
        r = client.post("/webhooks/gupshup", json={
            "app": "test", "type": "template-event",
            "payload": {"elementName": "t1", "status": "approved"},
        })
        assert r.status_code == 200


class TestWhatsAppRoutes:
    def test_routes_registered(self):
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/whatsapp/status" in routes
        assert "/whatsapp/onboarding/start" in routes
        assert "/whatsapp/templates" in routes
        assert "/whatsapp/send/template" in routes
        assert "/whatsapp/send/session" in routes
        assert "/whatsapp/window/{contact_id}" in routes


class TestWindowLogic:
    @pytest.mark.asyncio
    async def test_window_closed_no_inbound(self):
        from app.api.whatsapp import check_24hr_window
        from unittest.mock import MagicMock
        contact = MagicMock()
        contact.last_inbound_whatsapp_at = None
        result = await check_24hr_window(contact)
        assert not result["is_open"]
        assert result["requires_template"]

    @pytest.mark.asyncio
    async def test_window_open(self):
        from app.api.whatsapp import check_24hr_window
        from unittest.mock import MagicMock
        from datetime import datetime, timezone, timedelta
        contact = MagicMock()
        contact.last_inbound_whatsapp_at = datetime.now(timezone.utc) - timedelta(hours=2)
        result = await check_24hr_window(contact)
        assert result["is_open"]
        assert not result["requires_template"]

    @pytest.mark.asyncio
    async def test_window_expired(self):
        from app.api.whatsapp import check_24hr_window
        from unittest.mock import MagicMock
        from datetime import datetime, timezone, timedelta
        contact = MagicMock()
        contact.last_inbound_whatsapp_at = datetime.now(timezone.utc) - timedelta(hours=30)
        result = await check_24hr_window(contact)
        assert not result["is_open"]
        assert result["requires_template"]


class TestSecurityWhatsApp:
    def test_status_does_not_expose_tokens(self):
        from app.api.whatsapp import get_whatsapp_status
        import inspect
        src = inspect.getsource(get_whatsapp_status)
        assert "gupshup_app_token" not in src
        assert "partner_token" not in src

    def test_webhook_no_secrets(self):
        r = client.post("/webhooks/gupshup", json={"type": "unknown"})
        assert "token" not in r.text.lower()
        assert "password" not in r.text.lower()
