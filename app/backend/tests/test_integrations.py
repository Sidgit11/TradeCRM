"""Tests for integration services — Gupshup, SendGrid, Gmail."""
import pytest

from app.integrations.gupshup import GupshupService, SendResult
from app.integrations.sendgrid_service import SendGridService, EmailSendResult, WARMUP_SCHEDULE
from app.integrations import gmail_service


class TestGupshupService:
    def test_unconfigured_returns_mock(self):
        service = GupshupService(api_key="", app_id="")
        assert not service.is_configured

    @pytest.mark.asyncio
    async def test_send_template_mock(self):
        service = GupshupService(api_key="", app_id="")
        result = await service.send_template_message(
            phone="+49170123456",
            template_name="buyer_intro",
            variables={"name": "Hans"},
        )
        assert result.success
        assert "mock" in result.message_id

    @pytest.mark.asyncio
    async def test_send_session_mock(self):
        service = GupshupService(api_key="", app_id="")
        result = await service.send_session_message(
            phone="+49170123456",
            text="Hello, following up on our conversation.",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_get_templates_mock(self):
        service = GupshupService(api_key="", app_id="")
        templates = await service.get_templates()
        assert len(templates) >= 1
        assert templates[0].name == "buyer_intro"
        assert templates[0].status == "APPROVED"

    @pytest.mark.asyncio
    async def test_parse_status_webhook(self):
        service = GupshupService()
        event = await service.parse_webhook({
            "type": "message-event",
            "payload": {
                "id": "msg123",
                "type": "delivered",
                "destination": "+49170123456",
            },
            "timestamp": "1711900000",
        })
        assert event["kind"] == "status_update"
        assert event["message_id"] == "msg123"
        assert event["status"] == "delivered"

    @pytest.mark.asyncio
    async def test_parse_inbound_webhook(self):
        service = GupshupService()
        event = await service.parse_webhook({
            "type": "message",
            "payload": {
                "source": "+49170123456",
                "id": "inbound_123",
                "payload": {"text": "Yes, interested in black pepper"},
            },
            "timestamp": "1711900000",
        })
        assert event["kind"] == "inbound_message"
        assert event["phone"] == "+49170123456"
        assert "pepper" in event["text"]

    @pytest.mark.asyncio
    async def test_parse_unknown_webhook(self):
        service = GupshupService()
        event = await service.parse_webhook({"type": "unknown"})
        assert event["kind"] == "unknown"


class TestSendGridService:
    def test_unconfigured_returns_mock(self):
        service = SendGridService(api_key="")
        assert not service.is_configured

    @pytest.mark.asyncio
    async def test_send_email_mock(self):
        service = SendGridService(api_key="")
        result = await service.send_email(
            to_email="buyer@example.com",
            from_name="Spice Exports",
            from_email="hello@spiceexports.com",
            subject="Premium Pepper from Kerala",
            html_body="<p>Hello, we have fresh stock.</p>",
        )
        assert result.success
        assert "mock" in result.message_id

    def test_warmup_schedule_day_0(self):
        service = SendGridService()
        assert service.get_warmup_limit(0) == 20

    def test_warmup_schedule_day_5(self):
        service = SendGridService()
        assert service.get_warmup_limit(5) == 150

    def test_warmup_schedule_beyond_max(self):
        service = SendGridService()
        limit = service.get_warmup_limit(100)
        assert limit == WARMUP_SCHEDULE[-1]

    @pytest.mark.asyncio
    async def test_send_with_warmup_under_limit(self):
        service = SendGridService(api_key="")
        result = await service.send_with_warmup(
            tenant_warmup_day=0,
            tenant_sent_today=10,
            to_email="buyer@example.com",
            from_name="Test",
            from_email="test@test.com",
            subject="Test",
            html_body="<p>Test</p>",
        )
        assert result.success

    @pytest.mark.asyncio
    async def test_send_with_warmup_over_limit(self):
        service = SendGridService(api_key="")
        result = await service.send_with_warmup(
            tenant_warmup_day=0,
            tenant_sent_today=20,  # limit is 20 on day 0
            to_email="buyer@example.com",
            from_name="Test",
            from_email="test@test.com",
            subject="Test",
            html_body="<p>Test</p>",
        )
        assert not result.success
        assert "warmup limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_parse_webhook_events(self):
        service = SendGridService()
        events = await service.parse_webhook([
            {"event": "delivered", "sg_message_id": "abc123.1", "email": "test@test.com", "timestamp": 1711900000},
            {"event": "open", "sg_message_id": "abc123.1", "email": "test@test.com", "timestamp": 1711900060},
        ])
        assert len(events) == 2
        assert events[0]["event_type"] == "delivered"
        assert events[0]["message_id"] == "abc123"
        assert events[1]["event_type"] == "open"


class TestGmailService:
    def test_auth_url_generation(self):
        """Test that auth URL is generated correctly (requires GOOGLE_CLIENT_ID set)."""
        from app.config import settings
        if not settings.GOOGLE_CLIENT_ID:
            pytest.skip("GOOGLE_CLIENT_ID not configured")
        url = gmail_service.get_auth_url(state="test_state")
        assert "accounts.google.com" in url
        assert "test_state" in url

    def test_scopes_include_required_permissions(self):
        assert "https://www.googleapis.com/auth/gmail.readonly" in gmail_service.SCOPES
        assert "https://www.googleapis.com/auth/gmail.send" in gmail_service.SCOPES
        assert "https://www.googleapis.com/auth/gmail.modify" in gmail_service.SCOPES

    def test_client_config_structure(self):
        config = gmail_service._get_client_config()
        assert "web" in config
        assert "client_id" in config["web"]
        assert "client_secret" in config["web"]
        assert "redirect_uris" in config["web"]
