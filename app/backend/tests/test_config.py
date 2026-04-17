"""Tests for application configuration."""
import os

import pytest

from app.config import Settings


class TestSettings:
    def test_default_values(self):
        """Settings should have sensible defaults for local development."""
        s = Settings(_env_file=None)
        assert "postgresql+asyncpg" in s.DATABASE_URL
        assert "redis" in s.REDIS_URL
        assert s.FRONTEND_URL == "http://localhost:3000"
        assert s.BACKEND_URL == "http://localhost:8000"

    def test_database_url_format(self):
        """DATABASE_URL must use asyncpg driver."""
        s = Settings(_env_file=None)
        assert s.DATABASE_URL.startswith("postgresql+asyncpg://")

    def test_all_api_keys_default_empty(self):
        """API keys should default to empty string, never None."""
        s = Settings(_env_file=None)
        assert s.ANTHROPIC_API_KEY == ""
        assert s.GUPSHUP_API_KEY == ""
        assert s.SENDGRID_API_KEY == ""
        assert s.STRIPE_SECRET_KEY == ""
        assert s.BRAVE_SEARCH_API_KEY == ""

    def test_clerk_keys_default_empty(self):
        """Clerk auth keys should default to empty string."""
        s = Settings(_env_file=None)
        assert s.CLERK_SECRET_KEY == ""
        assert s.CLERK_PUBLISHABLE_KEY == ""
        assert s.CLERK_JWT_ISSUER == ""
