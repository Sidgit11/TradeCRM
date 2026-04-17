"""Tests for Phase 4 API endpoints — Campaigns, Inbox, Pipeline.
Auth tests are covered by test_full_system.py::TestSecurityAllEndpointsRequireAuth.
"""
import uuid
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.campaigns import CampaignCreate, CampaignStepCreate, CampaignAnalytics
from app.schemas.inbox import ConversationSummary, ReplyRequest
from app.schemas.pipeline import OpportunityCreate, OpportunityMoveRequest, PipelineStats

client = TestClient(app)


class TestCampaignSchemas:
    def test_valid_campaign_create(self):
        c = CampaignCreate(
            name="Pepper EU Q1", type="multi_channel",
            steps=[
                CampaignStepCreate(channel="whatsapp", delay_days=0, condition="always"),
                CampaignStepCreate(channel="email", delay_days=3, condition="no_reply"),
            ],
        )
        assert c.name == "Pepper EU Q1"
        assert len(c.steps) == 2
        assert c.steps[1].delay_days == 3

    def test_campaign_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            CampaignCreate(name="", type="email")

    def test_campaign_analytics_schema(self):
        a = CampaignAnalytics(
            total_sent=100, delivered=90, delivery_rate=90.0,
            opened=40, open_rate=44.4,
            replied=10, reply_rate=11.1,
            failed=5, bounced=5,
        )
        assert a.delivery_rate == 90.0


class TestInboxSchemas:
    def test_reply_request(self):
        r = ReplyRequest(channel="whatsapp", body="Hello, thanks for your interest!")
        assert r.subject is None

    def test_reply_request_email(self):
        r = ReplyRequest(channel="email", body="Dear Hans,\n\nThank you.", subject="Re: Pepper Inquiry")
        assert r.subject == "Re: Pepper Inquiry"

    def test_conversation_summary(self):
        c = ConversationSummary(
            contact_id="abc", contact_name="Hans Mueller",
            company_name="German Importer",
            last_message_preview="Yes, interested in...",
            channel="whatsapp", unread_count=2,
            classification="interested",
        )
        assert c.unread_count == 2


class TestPipelineSchemas:
    def test_opportunity_create(self):
        o = OpportunityCreate(
            company_id=uuid.uuid4(),
            value=50000, commodity="pepper",
            source="discovery",
        )
        assert o.value == 50000
        assert o.source == "discovery"

    def test_pipeline_stats(self):
        s = PipelineStats(total_opportunities=15, total_value=250000)
        assert s.total_opportunities == 15


class TestAllPhase4RoutesRegistered:
    def test_campaign_routes(self):
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/campaigns" in routes
        assert "/campaigns/{campaign_id}" in routes
        assert "/campaigns/{campaign_id}/steps" in routes
        assert "/campaigns/{campaign_id}/activate" in routes
        assert "/campaigns/{campaign_id}/pause" in routes
        assert "/campaigns/{campaign_id}/cancel" in routes
        assert "/campaigns/{campaign_id}/analytics" in routes

    def test_inbox_routes(self):
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/inbox/conversations" in routes
        assert "/inbox/conversations/{contact_id}" in routes
        assert "/inbox/conversations/{contact_id}/reply" in routes
        assert "/inbox/conversations/{contact_id}/close" in routes
        assert "/inbox/suggestions" in routes
        assert "/inbox/suggestions/{suggestion_id}/approve" in routes
        assert "/inbox/suggestions/{suggestion_id}/reject" in routes

    def test_pipeline_routes(self):
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/pipeline" in routes
        assert "/pipeline/stages" in routes
        assert "/pipeline/stats" in routes
        assert "/pipeline/{opp_id}" in routes
        assert "/pipeline/{opp_id}/move" in routes
