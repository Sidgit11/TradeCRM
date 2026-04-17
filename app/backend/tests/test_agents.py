"""Tests for AI agents — Research, Composer, Reply, Analytics."""
import pytest

from app.agents.research_agent import ResearchAgent
from app.agents.composer_agent import ComposerAgent
from app.agents.reply_agent import ReplyAgent, CLASSIFICATION_KEYWORDS
from app.agents.analytics_agent import AnalyticsAgent


class TestResearchAgent:
    @pytest.mark.asyncio
    async def test_run_returns_structured_profile(self):
        agent = ResearchAgent()
        result = await agent.run("Euro Spice BV", country="Netherlands")
        assert "company_overview" in result
        assert "trade_intelligence" in result
        assert "key_people" in result
        assert "sources" in result
        assert "confidence_score" in result
        assert isinstance(result["confidence_score"], float)

    @pytest.mark.asyncio
    async def test_run_with_website(self):
        agent = ResearchAgent()
        result = await agent.run(
            "Test Company",
            country="Germany",
            website="https://httpbin.org/html",
        )
        assert result["company_overview"]["website"] == "https://httpbin.org/html"

    @pytest.mark.asyncio
    async def test_web_search_returns_mock_when_unconfigured(self):
        agent = ResearchAgent()
        results = await agent._web_search("pepper importer")
        assert len(results) >= 1

    def test_confidence_calculation_empty_profile(self):
        agent = ResearchAgent()
        score = agent._calculate_confidence({
            "company_overview": {},
            "trade_intelligence": {},
            "key_people": [],
        })
        assert score == 0.0

    def test_confidence_calculation_with_name(self):
        agent = ResearchAgent()
        score = agent._calculate_confidence({
            "company_overview": {"name": "Test Co"},
            "trade_intelligence": {},
            "key_people": [],
        })
        assert score > 0.0

    def test_risk_analysis_no_website(self):
        agent = ResearchAgent()
        risks = agent._analyze_risks({
            "company_overview": {"website": None},
            "trade_intelligence": {},
        })
        assert any("website" in r["signal"].lower() for r in risks)


class TestComposerAgent:
    @pytest.mark.asyncio
    async def test_compose_whatsapp_message(self):
        agent = ComposerAgent()
        result = await agent.compose(
            contact_name="Hans Mueller",
            contact_title="Purchasing Manager",
            company_name="German Importer GmbH",
            company_data={"commodities": ["pepper"]},
            channel="whatsapp",
            campaign_context=None,
            tenant_profile={"company_name": "Spice Exports Inc", "commodities": ["pepper", "cloves"]},
        )
        assert result["body"]
        assert len(result["body"]) < 500  # WhatsApp should be concise
        assert "Hans" in result["body"]
        assert result["subject"] is None  # WhatsApp has no subject
        assert result["personalization_explanation"]

    @pytest.mark.asyncio
    async def test_compose_email_message(self):
        agent = ComposerAgent()
        result = await agent.compose(
            contact_name="Hans Mueller",
            contact_title=None,
            company_name="German Importer GmbH",
            company_data=None,
            channel="email",
            campaign_context=None,
            tenant_profile={"company_name": "Spice Exports Inc", "commodities": ["pepper"]},
        )
        assert result["subject"]
        assert result["body"]
        assert "Hans" in result["body"]
        assert "Spice Exports" in result["body"]

    @pytest.mark.asyncio
    async def test_compose_followup(self):
        agent = ComposerAgent()
        result = await agent.compose(
            contact_name="Hans Mueller",
            contact_title=None,
            company_name=None,
            company_data=None,
            channel="whatsapp",
            campaign_context="Follow up on previous message",
            tenant_profile={"company_name": "Spice Co", "commodities": ["pepper"]},
        )
        assert "follow" in result["body"].lower()

    @pytest.mark.asyncio
    async def test_compose_never_mentions_pricing(self):
        agent = ComposerAgent()
        result = await agent.compose(
            contact_name="Test",
            contact_title=None,
            company_name="Test Co",
            company_data=None,
            channel="email",
            campaign_context=None,
            tenant_profile={"company_name": "Seller", "commodities": ["pepper"]},
        )
        body_lower = result["body"].lower()
        assert "$" not in body_lower
        assert "usd" not in body_lower


class TestReplyAgent:
    @pytest.mark.asyncio
    async def test_classify_interested(self):
        agent = ReplyAgent()
        result = await agent.analyze("Yes, I am interested. Please send more details.")
        assert result["classification"] == "interested"
        assert result["confidence"] >= 0.7

    @pytest.mark.asyncio
    async def test_classify_price_inquiry(self):
        agent = ReplyAgent()
        result = await agent.analyze("What is your price for black pepper 500GL?")
        assert result["classification"] == "price_inquiry"

    @pytest.mark.asyncio
    async def test_classify_sample_request(self):
        agent = ReplyAgent()
        result = await agent.analyze("Can you send us samples of your pepper grades?")
        assert result["classification"] == "sample_request"

    @pytest.mark.asyncio
    async def test_classify_meeting_request(self):
        agent = ReplyAgent()
        result = await agent.analyze("Can we schedule a call to discuss further?")
        assert result["classification"] == "meeting_request"

    @pytest.mark.asyncio
    async def test_classify_not_interested(self):
        agent = ReplyAgent()
        result = await agent.analyze("Not interested, please stop contacting me.")
        assert result["classification"] == "not_interested"

    @pytest.mark.asyncio
    async def test_classify_out_of_office(self):
        agent = ReplyAgent()
        result = await agent.analyze("I am out of office until January 15th. For urgent matters contact my colleague.")
        assert result["classification"] == "out_of_office"

    @pytest.mark.asyncio
    async def test_reply_never_commits_to_price(self):
        agent = ReplyAgent()
        result = await agent.analyze("What is your best price?")
        reply = result["suggested_reply"].lower()
        assert "$" not in reply
        assert "usd" not in reply

    @pytest.mark.asyncio
    async def test_out_of_office_no_reply(self):
        agent = ReplyAgent()
        result = await agent.analyze("Auto-reply: I am on vacation.")
        assert result["suggested_reply"] == "" or result["classification"] == "out_of_office"

    @pytest.mark.asyncio
    async def test_result_has_explanation(self):
        agent = ReplyAgent()
        result = await agent.analyze("Yes please, send your catalogue")
        assert result["explanation"]
        assert isinstance(result["explanation"], str)


class TestAnalyticsAgent:
    @pytest.mark.asyncio
    async def test_good_campaign(self):
        agent = AnalyticsAgent()
        result = await agent.analyze_campaign(
            campaign_name="Pepper EU Q1",
            stats={"total_sent": 100, "delivered": 95, "opened": 40, "replied": 15, "failed": 2, "bounced": 3},
        )
        assert result["health"] == "good"
        assert result["metrics"]["reply_rate"] == 15.8  # 15/95*100
        assert "Pepper EU Q1" in result["summary"]

    @pytest.mark.asyncio
    async def test_poor_campaign(self):
        agent = AnalyticsAgent()
        result = await agent.analyze_campaign(
            campaign_name="Cold Outreach",
            stats={"total_sent": 50, "delivered": 45, "opened": 5, "replied": 0, "failed": 3, "bounced": 2},
        )
        assert result["health"] == "poor"
        assert len(result["recommendations"]) > 0

    @pytest.mark.asyncio
    async def test_high_bounce_triggers_recommendation(self):
        agent = AnalyticsAgent()
        result = await agent.analyze_campaign(
            campaign_name="Test",
            stats={"total_sent": 100, "delivered": 80, "opened": 20, "replied": 5, "failed": 5, "bounced": 15},
        )
        assert any("bounce" in r.lower() for r in result["recommendations"])

    @pytest.mark.asyncio
    async def test_empty_campaign(self):
        agent = AnalyticsAgent()
        result = await agent.analyze_campaign(
            campaign_name="Empty",
            stats={"total_sent": 0, "delivered": 0, "opened": 0, "replied": 0, "failed": 0, "bounced": 0},
        )
        assert result["metrics"]["total_sent"] == 0
        assert result["health"] == "poor"

    @pytest.mark.asyncio
    async def test_step_stats_recommendation(self):
        agent = AnalyticsAgent()
        result = await agent.analyze_campaign(
            campaign_name="Multi-step",
            stats={"total_sent": 60, "delivered": 55, "opened": 20, "replied": 8, "failed": 2, "bounced": 3},
            step_stats=[
                {"step_number": 1, "channel": "email", "sent": 30, "delivered": 28, "replied": 2},
                {"step_number": 2, "channel": "whatsapp", "sent": 30, "delivered": 27, "replied": 6},
            ],
        )
        assert any("Step 2" in r for r in result["recommendations"])
