"""Tests for Phase 3 API endpoints — Agents, Discovery, Enrichment.
Auth tests are covered by test_full_system.py::TestSecurityAllEndpointsRequireAuth.
"""
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestAllRoutesRegistered:
    """Verify all Phase 3 routes are registered."""

    def test_agent_routes_exist(self):
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/agents/run" in routes
        assert "/agents/tasks" in routes
        assert "/agents/tasks/{task_id}" in routes

    def test_discover_routes_exist(self):
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/discover/search" in routes
        assert "/discover/save" in routes

    def test_enrichment_routes_exist(self):
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/companies/{company_id}/research" in routes
        assert "/companies/{company_id}/find-contacts" in routes
