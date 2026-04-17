"""Tests for the health check endpoint and CORS."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_returns_200(self):
        response = client.get("/health")
        assert response.status_code == 200

    def test_returns_healthy_status(self):
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_returns_version(self):
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert data["version"] == "0.1.0"


class TestCORS:
    def test_cors_headers_for_allowed_origin(self):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"

    def test_cors_rejects_unknown_origin(self):
        response = client.options(
            "/health",
            headers={
                "Origin": "http://evil.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.headers.get("access-control-allow-origin") != "http://evil.com"
