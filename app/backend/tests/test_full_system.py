"""Full system validation tests — cross-cutting concerns, security, completeness."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base

client = TestClient(app)


class TestSystemHealth:
    def test_health_endpoint(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "healthy"

    def test_openapi_schema_loads(self):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "paths" in schema
        assert len(schema["paths"]) > 50  # we have 60+ endpoints


class TestSecurityAllEndpointsRequireAuth:
    """Every non-public endpoint must return 401/403 without auth.
    Skipped when DEV_MODE=true since auth is bypassed.
    """

    PUBLIC_PATHS = {"/health", "/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    WEBHOOK_PATHS = {"/webhooks/gupshup", "/webhooks/sendgrid", "/webhooks/stripe", "/webhooks/clerk"}
    PUBLIC_DATA_PATHS = {"/catalog/ports", "/catalog/products/template/download", "/catalog/commodities/search",
                         "/email/callback/gmail"}

    def _get_protected_routes(self):
        routes = []
        for route in app.routes:
            if not hasattr(route, "methods") or not hasattr(route, "path"):
                continue
            path = route.path
            if path in self.PUBLIC_PATHS or path in self.WEBHOOK_PATHS or path in self.PUBLIC_DATA_PATHS:
                continue
            if "{" in path:
                path = path.replace("{campaign_id}", "00000000-0000-0000-0000-000000000000")
                path = path.replace("{company_id}", "00000000-0000-0000-0000-000000000000")
                path = path.replace("{contact_id}", "00000000-0000-0000-0000-000000000000")
                path = path.replace("{list_id}", "00000000-0000-0000-0000-000000000000")
                path = path.replace("{member_id}", "00000000-0000-0000-0000-000000000000")
                path = path.replace("{task_id}", "00000000-0000-0000-0000-000000000000")
                path = path.replace("{suggestion_id}", "00000000-0000-0000-0000-000000000000")
                path = path.replace("{step_id}", "00000000-0000-0000-0000-000000000000")
                path = path.replace("{opp_id}", "00000000-0000-0000-0000-000000000000")
            for method in route.methods:
                if method in ("GET", "POST", "PUT", "DELETE"):
                    routes.append((method, path))
        return routes

    def test_all_get_endpoints_require_auth(self):
        from app.config import settings
        if settings.DEV_MODE:
            pytest.skip("DEV_MODE is on — auth bypassed")
        for method, path in self._get_protected_routes():
            if method != "GET":
                continue
            r = client.get(path)
            assert r.status_code in (401, 403, 405), (
                f"GET {path} returned {r.status_code} — must require auth"
            )

    def test_all_post_endpoints_require_auth(self):
        from app.config import settings
        if settings.DEV_MODE:
            pytest.skip("DEV_MODE is on — auth bypassed")
        for method, path in self._get_protected_routes():
            if method != "POST":
                continue
            r = client.post(path, json={})
            assert r.status_code in (401, 403, 422), (
                f"POST {path} returned {r.status_code} — must require auth"
            )

    def test_all_put_endpoints_require_auth(self):
        from app.config import settings
        if settings.DEV_MODE:
            pytest.skip("DEV_MODE is on — auth bypassed")
        for method, path in self._get_protected_routes():
            if method != "PUT":
                continue
            r = client.put(path, json={})
            assert r.status_code in (401, 403, 422), (
                f"PUT {path} returned {r.status_code} — must require auth"
            )

    def test_all_delete_endpoints_require_auth(self):
        from app.config import settings
        if settings.DEV_MODE:
            pytest.skip("DEV_MODE is on — auth bypassed")
        for method, path in self._get_protected_routes():
            if method != "DELETE":
                continue
            r = client.delete(path)
            assert r.status_code in (401, 403), (
                f"DELETE {path} returned {r.status_code} — must require auth"
            )


class TestWebhooksArePublic:
    """Webhooks must accept requests without auth (they use signature verification)."""

    def test_gupshup_webhook_public(self):
        r = client.post("/webhooks/gupshup", json={"type": "message-event", "payload": {}})
        assert r.status_code == 200

    def test_sendgrid_webhook_public(self):
        r = client.post("/webhooks/sendgrid", json=[{"event": "delivered"}])
        assert r.status_code == 200

    def test_stripe_webhook_public(self):
        r = client.post("/webhooks/stripe", content=b"test")
        assert r.status_code == 200


class TestDatabaseSchemaCompleteness:
    """Validate the database schema covers all required tables."""

    REQUIRED_TABLES = {
        "tenants", "users", "contacts", "contact_lists", "contact_list_members",
        "companies", "campaigns", "campaign_steps", "messages", "message_events",
        "reply_suggestions", "sequences", "pipeline_stages", "pipeline_opportunities",
        "activity_log", "credit_transactions", "agent_tasks",
        "allowed_emails",
        "ports", "products", "product_varieties", "product_grades",
        "fob_prices", "freight_rates", "tenant_defaults",
        "commodity_references", "email_accounts",
        "whatsapp_templates", "inbound_leads", "lead_preferences",
        "message_templates",
        "shipments", "company_shipment_summaries", "product_port_interests",
    }

    def test_all_tables_defined(self):
        defined_tables = set(Base.metadata.tables.keys())
        for table in self.REQUIRED_TABLES:
            assert table in defined_tables, f"Missing table: {table}"

    def test_no_extra_tables(self):
        """Ensure we haven't accidentally created tables not in the spec."""
        defined_tables = set(Base.metadata.tables.keys())
        extra = defined_tables - self.REQUIRED_TABLES
        # Allow empty — if there are extras, they should be intentional
        for table in extra:
            assert False, f"Unexpected table: {table}. Add to REQUIRED_TABLES if intentional."


class TestCORSSecurity:
    def test_cors_allows_configured_origin(self):
        r = client.options("/health", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        })
        assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_blocks_unknown_origin(self):
        r = client.options("/health", headers={
            "Origin": "https://attacker.com",
            "Access-Control-Request-Method": "GET",
        })
        assert r.headers.get("access-control-allow-origin") != "https://attacker.com"


class TestRouteCount:
    """Verify we have the expected number of endpoints."""

    def test_minimum_endpoint_count(self):
        routes = [r for r in app.routes if hasattr(r, "methods")]
        endpoint_count = len(routes)
        assert endpoint_count >= 60, f"Expected 60+ endpoints, got {endpoint_count}"
