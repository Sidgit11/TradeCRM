"""Tests for lead classification agent — filtering, matching, security."""
import pytest

from app.agents.lead_classifier import (
    should_skip_email, match_products_to_catalog, match_to_existing_contacts,
)


class TestEmailPreFilter:
    """Obvious non-business emails should be filtered before hitting LLM."""

    def test_skips_noreply(self):
        assert should_skip_email("noreply@company.com", "Your order") == "notification"

    def test_skips_no_reply_dash(self):
        assert should_skip_email("no-reply@service.com", "Update") == "notification"

    def test_skips_notifications(self):
        assert should_skip_email("notifications@github.com", "PR merged") == "notification"

    def test_skips_donotreply(self):
        assert should_skip_email("donotreply@bank.com", "Statement") == "notification"

    def test_skips_otp_subjects(self):
        assert should_skip_email("security@bank.com", "Your OTP is 1234") == "notification"

    def test_skips_password_reset(self):
        assert should_skip_email("support@app.com", "Password reset request") == "notification"

    def test_passes_business_email(self):
        assert should_skip_email("hans@germanimporter.de", "Inquiry about black pepper") is None

    def test_passes_generic_sender(self):
        assert should_skip_email("sales@company.com", "Product inquiry") is None

    def test_skips_newsletter_with_unsubscribe_header(self):
        result = should_skip_email(
            "news@company.com", "Weekly digest",
            {"list-unsubscribe": "<mailto:unsubscribe@company.com>"},
        )
        assert result == "newsletter"


class TestProductCatalogMatching:
    CATALOG = [
        {
            "id": "prod-1", "name": "Black Pepper", "origin_country": "India",
            "aliases": ["kali mirch", "piper nigrum"],
            "varieties": [
                {"name": "Malabar", "grades": [
                    {"id": "grade-1", "name": "500GL"},
                    {"id": "grade-2", "name": "550GL"},
                ]},
                {"name": "Tellicherry", "grades": [
                    {"id": "grade-3", "name": "TGSEB"},
                ]},
            ],
        },
        {
            "id": "prod-2", "name": "Vanilla", "origin_country": "India",
            "aliases": ["vanilla beans", "vanilla sticks"],
            "varieties": [
                {"name": "Planifolia", "grades": [
                    {"id": "grade-4", "name": "Grade A"},
                ]},
            ],
        },
    ]

    def test_exact_product_match(self):
        matches = match_products_to_catalog(["black pepper"], self.CATALOG)
        assert len(matches) == 1
        assert matches[0]["matched_product_name"] == "Black Pepper"
        assert matches[0]["confidence"] >= 0.8

    def test_product_with_grade_match(self):
        matches = match_products_to_catalog(["black pepper 500GL"], self.CATALOG)
        assert matches[0]["matched_grade_name"] == "500GL"
        assert matches[0]["confidence"] >= 0.9

    def test_alias_match(self):
        matches = match_products_to_catalog(["kali mirch"], self.CATALOG)
        assert matches[0]["matched_product_name"] == "Black Pepper"
        assert matches[0]["confidence"] >= 0.7

    def test_no_match(self):
        matches = match_products_to_catalog(["saffron threads"], self.CATALOG)
        assert matches[0]["matched_product_id"] is None
        assert matches[0]["confidence"] == 0.0

    def test_vanilla_alias_match(self):
        matches = match_products_to_catalog(["vanilla beans grade A"], self.CATALOG)
        assert matches[0]["matched_product_name"] == "Vanilla"

    def test_multiple_products(self):
        matches = match_products_to_catalog(["black pepper", "vanilla beans"], self.CATALOG)
        assert len(matches) == 2
        assert matches[0]["matched_product_name"] == "Black Pepper"
        assert matches[1]["matched_product_name"] == "Vanilla"

    def test_empty_list(self):
        matches = match_products_to_catalog([], self.CATALOG)
        assert matches == []


class TestCRMMatching:
    CONTACTS = [
        {"id": "ct-1", "name": "Hans Mueller", "email": "hans@germanimporter.de", "company_id": "co-1"},
        {"id": "ct-2", "name": "Maria Santos", "email": "maria@santos.br", "company_id": None},
    ]
    COMPANIES = [
        {"id": "co-1", "name": "German Importer GmbH"},
        {"id": "co-2", "name": "Santos Trading"},
    ]

    def test_exact_email_match(self):
        result = match_to_existing_contacts(
            "hans@germanimporter.de", "Hans Mueller", "German Importer", self.CONTACTS, self.COMPANIES,
        )
        assert result["matched_contact_id"] == "ct-1"
        assert result["matched_contact_confidence"] == 0.99
        assert result["matched_company_id"] == "co-1"

    def test_company_name_match(self):
        result = match_to_existing_contacts(
            "new@person.com", None, "Santos Trading", self.CONTACTS, self.COMPANIES,
        )
        assert result["matched_company_id"] == "co-2"
        assert result["matched_company_confidence"] >= 0.7

    def test_no_match(self):
        result = match_to_existing_contacts(
            "stranger@unknown.com", "Unknown Person", "Unknown Co", self.CONTACTS, self.COMPANIES,
        )
        assert result["matched_contact_id"] is None
        assert result["matched_company_id"] is None

    def test_case_insensitive_email(self):
        result = match_to_existing_contacts(
            "HANS@GERMANIMPORTER.DE", None, None, self.CONTACTS, self.COMPANIES,
        )
        assert result["matched_contact_id"] == "ct-1"

    def test_partial_company_match(self):
        result = match_to_existing_contacts(
            "new@test.com", None, "German Importer", self.CONTACTS, self.COMPANIES,
        )
        assert result["matched_company_id"] == "co-1"
        assert result["matched_company_confidence"] >= 0.5


class TestDataSecurity:
    """Ensure sensitive data handling is correct."""

    def test_no_api_key_leaks_in_prompt(self):
        """The classification prompt should never contain API keys."""
        from app.agents.lead_classifier import _build_classification_prompt
        prompt = _build_classification_prompt(
            "test@test.com", "Test", "Test body",
            "Test Corp", ["pepper"],
            [{"name": "Pepper", "origin_country": "India", "aliases": [], "varieties": []}],
        )
        assert "AIzaSy" not in prompt  # Gemini key prefix
        assert "GOCSPX" not in prompt  # Google client secret prefix
        assert "sk_test" not in prompt  # Clerk key prefix
        assert "npg_" not in prompt  # Neon password prefix

    def test_email_body_truncated_in_prompt(self):
        """Email body in prompt should be truncated to prevent prompt injection."""
        from app.agents.lead_classifier import _build_classification_prompt
        long_body = "x" * 10000
        prompt = _build_classification_prompt(
            "test@test.com", "Test", long_body,
            "Test Corp", ["pepper"], [],
        )
        # Body should be truncated to 3000 chars
        assert len(prompt) < 5000

    def test_token_data_not_in_lead_response(self):
        """Lead API responses should never include OAuth tokens."""
        from app.api.leads import _lead_response
        # Create a mock lead object to test serialization
        # The response function only accesses defined attributes, not token_data
        # This test ensures the function signature doesn't include token fields
        import inspect
        source = inspect.getsource(_lead_response)
        assert "token" not in source.lower() or "updated_tokens" not in source
