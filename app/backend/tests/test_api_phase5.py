"""Tests for Phase 5 — Dashboard, Billing, and full route verification.
Auth tests are covered by test_full_system.py::TestSecurityAllEndpointsRequireAuth.
"""
from fastapi.testclient import TestClient

from app.main import app
from app.api.billing import PLAN_LIMITS

client = TestClient(app)


class TestPlanLimits:
    def test_free_trial_limits(self):
        limits = PLAN_LIMITS["free_trial"]
        assert limits["messages"] == 50
        assert limits["enrichments"] == 10

    def test_starter_limits(self):
        limits = PLAN_LIMITS["starter"]
        assert limits["messages"] == 500
        assert limits["enrichments"] == 100

    def test_growth_limits(self):
        limits = PLAN_LIMITS["growth"]
        assert limits["messages"] == 2000
        assert limits["enrichments"] == 500

    def test_pro_unlimited_enrichments(self):
        limits = PLAN_LIMITS["pro"]
        assert limits["enrichments"] == -1  # unlimited

    def test_all_plans_defined(self):
        assert len(PLAN_LIMITS) == 4


class TestAllPhase5RoutesRegistered:
    def test_dashboard_routes(self):
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/dashboard/stats" in routes
        assert "/dashboard/activity" in routes
        assert "/dashboard/pending-approvals" in routes

    def test_billing_routes(self):
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/billing/credits" in routes
        assert "/billing/usage" in routes
        assert "/billing/create-checkout" in routes
        assert "/billing/create-portal" in routes
