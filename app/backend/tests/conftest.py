"""Shared test fixtures for the TradeCRM backend test suite."""
import uuid
from datetime import datetime, timezone

import pytest

from app.models.enums import (
    PlanType,
    UserRole,
    CampaignStatus,
    CampaignType,
    ChannelType,
    ContactEnrichmentStatus,
    ContactSource,
    CompanySource,
    EnrichmentStatus,
    MessageDirection,
    MessageStatus,
    StepCondition,
    SequenceStatus,
    OpportunitySource,
    ActorType,
    AgentTaskStatus,
    AgentTaskType,
    CreditActionType,
    ReplyClassification,
    SuggestionStatus,
)


@pytest.fixture
def tenant_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def other_tenant_id() -> uuid.UUID:
    """A second tenant for isolation tests."""
    return uuid.uuid4()


@pytest.fixture
def user_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture
def sample_tenant_data(tenant_id: uuid.UUID) -> dict:
    return {
        "id": tenant_id,
        "company_name": "Spice Exports Inc",
        "domain": "spiceexports.com",
        "plan": PlanType.starter,
        "commodities": ["pepper", "cardamom", "cloves"],
        "target_markets": ["USA", "Germany", "UAE"],
        "certifications": ["ISO 9001", "FSSAI"],
        "about": "Leading exporter of premium spices from Kerala, India",
    }


@pytest.fixture
def sample_user_data(user_id: uuid.UUID, tenant_id: uuid.UUID) -> dict:
    return {
        "id": user_id,
        "tenant_id": tenant_id,
        "supabase_user_id": f"sup_{uuid.uuid4().hex[:16]}",
        "email": "admin@spiceexports.com",
        "name": "Rajesh Kumar",
        "role": UserRole.admin,
        "is_active": True,
    }


@pytest.fixture
def sample_contact_data(tenant_id: uuid.UUID) -> dict:
    return {
        "tenant_id": tenant_id,
        "name": "Hans Mueller",
        "email": "hans@germanimporter.de",
        "phone": "+49170123456",
        "company_name": "German Importer GmbH",
        "title": "Head of Purchasing",
        "tags": ["pepper", "EU-buyer"],
        "custom_fields": {"preferred_language": "en"},
        "opted_in_whatsapp": True,
        "opted_in_email": True,
        "enrichment_status": ContactEnrichmentStatus.not_enriched,
        "source": ContactSource.manual,
    }


@pytest.fixture
def sample_company_data(tenant_id: uuid.UUID) -> dict:
    return {
        "tenant_id": tenant_id,
        "name": "Euro Spice Trading BV",
        "country": "Netherlands",
        "website": "https://eurospice.nl",
        "industry": "Spice Import & Distribution",
        "commodities": ["pepper", "turmeric"],
        "import_volume_annual": 5_000_000.00,
        "shipment_frequency": "monthly",
        "enrichment_status": EnrichmentStatus.not_enriched,
        "source": CompanySource.discovery,
        "confidence_score": 0.85,
    }
