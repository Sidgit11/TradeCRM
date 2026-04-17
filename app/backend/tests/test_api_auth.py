"""Tests for auth API endpoints."""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestSignup:
    def test_signup_requires_all_fields(self):
        response = client.post("/auth/signup", json={})
        assert response.status_code == 422

    def test_signup_requires_valid_email(self):
        response = client.post("/auth/signup", json={
            "company_name": "Test Co",
            "name": "Test User",
            "email": "not-an-email",
            "password": "password123",
        })
        assert response.status_code == 422

    def test_signup_requires_min_password_length(self):
        response = client.post("/auth/signup", json={
            "company_name": "Test Co",
            "name": "Test User",
            "email": "test@test.com",
            "password": "short",
        })
        assert response.status_code == 422


class TestLogin:
    def test_login_requires_email_and_password(self):
        response = client.post("/auth/login", json={})
        assert response.status_code == 422


class TestMe:
    def test_me_requires_auth(self):
        from app.config import settings
        if settings.DEV_MODE: pytest.skip("DEV_MODE")
        response = client.get("/auth/me")
        assert response.status_code in (401, 403)


class TestWebhooks:
    def test_gupshup_webhook_accepts_payload(self):
        response = client.post("/webhooks/gupshup", json={
            "type": "message-event",
            "payload": {"id": "test", "type": "delivered", "destination": "+1234"},
            "timestamp": "123456",
        })
        assert response.status_code == 200

    def test_sendgrid_webhook_accepts_events(self):
        response = client.post("/webhooks/sendgrid", json=[
            {"event": "delivered", "sg_message_id": "abc.1", "email": "test@test.com"},
        ])
        assert response.status_code == 200

    def test_stripe_webhook_placeholder(self):
        response = client.post("/webhooks/stripe", content=b"test")
        assert response.status_code == 200
