"""Tests for database models — validates schema correctness and enum consistency."""
import uuid
from datetime import date, datetime, timezone

import pytest

from app.database import Base
from app.models import (
    Tenant, User, Contact, ContactList, ContactListMember,
    Company, Campaign, CampaignStep, Message, MessageEvent,
    ReplySuggestion, Sequence, PipelineStage, PipelineOpportunity,
    ActivityLog, CreditTransaction, AgentTask,
)
from app.models.enums import (
    PlanType, UserRole, ContactEnrichmentStatus, ContactSource,
    CompanySource, EnrichmentStatus, CampaignType, CampaignStatus,
    ChannelType, StepCondition, MessageDirection, MessageStatus,
    MessageEventType, ReplyClassification, SuggestionStatus,
    SequenceStatus, OpportunitySource, ActorType, CreditActionType,
    AgentTaskType, AgentTaskStatus,
)


class TestBaseModel:
    def test_base_has_id_field(self):
        """All models must inherit from Base which provides UUID id."""
        assert hasattr(Base, "id")
        assert hasattr(Base, "created_at")
        assert hasattr(Base, "updated_at")


class TestTenantModel:
    def test_table_name(self):
        assert Tenant.__tablename__ == "tenants"

    def test_required_fields(self):
        columns = {c.name for c in Tenant.__table__.columns}
        required = {"id", "company_name", "plan", "created_at", "updated_at"}
        assert required.issubset(columns)

    def test_json_fields_exist(self):
        columns = {c.name for c in Tenant.__table__.columns}
        assert "commodities" in columns
        assert "target_markets" in columns
        assert "certifications" in columns

    def test_no_tenant_id_on_tenant(self):
        """Tenants table must NOT have a tenant_id FK — it IS the root."""
        columns = {c.name for c in Tenant.__table__.columns}
        assert "tenant_id" not in columns


class TestUserModel:
    def test_table_name(self):
        assert User.__tablename__ == "users"

    def test_has_tenant_id(self):
        columns = {c.name for c in User.__table__.columns}
        assert "tenant_id" in columns

    def test_has_supabase_user_id(self):
        columns = {c.name for c in User.__table__.columns}
        assert "supabase_user_id" in columns

    def test_role_enum_values(self):
        assert UserRole.admin.value == "admin"
        assert UserRole.member.value == "member"


class TestContactModel:
    def test_table_name(self):
        assert Contact.__tablename__ == "contacts"

    def test_has_tenant_id(self):
        columns = {c.name for c in Contact.__table__.columns}
        assert "tenant_id" in columns

    def test_has_soft_delete(self):
        columns = {c.name for c in Contact.__table__.columns}
        assert "is_deleted" in columns

    def test_composite_indexes_exist(self):
        """Verify composite indexes for performance-critical queries."""
        index_names = {idx.name for idx in Contact.__table__.indexes}
        assert "ix_contacts_tenant_email" in index_names
        assert "ix_contacts_tenant_phone" in index_names


class TestCompanyModel:
    def test_table_name(self):
        assert Company.__tablename__ == "companies"

    def test_enrichment_status_enum(self):
        assert EnrichmentStatus.not_enriched.value == "not_enriched"
        assert EnrichmentStatus.enriching.value == "enriching"
        assert EnrichmentStatus.partially_enriched.value == "partially_enriched"
        assert EnrichmentStatus.enriched.value == "enriched"

    def test_has_soft_delete(self):
        columns = {c.name for c in Company.__table__.columns}
        assert "is_deleted" in columns


class TestCampaignModel:
    def test_table_name(self):
        assert Campaign.__tablename__ == "campaigns"

    def test_campaign_types(self):
        assert CampaignType.email.value == "email"
        assert CampaignType.whatsapp.value == "whatsapp"
        assert CampaignType.multi_channel.value == "multi_channel"

    def test_campaign_statuses(self):
        assert CampaignStatus.draft.value == "draft"
        assert CampaignStatus.active.value == "active"
        assert CampaignStatus.cancelled.value == "cancelled"


class TestCampaignStepModel:
    def test_table_name(self):
        assert CampaignStep.__tablename__ == "campaign_steps"

    def test_step_conditions(self):
        assert StepCondition.no_reply.value == "no_reply"
        assert StepCondition.no_open.value == "no_open"
        assert StepCondition.always.value == "always"


class TestMessageModel:
    def test_table_name(self):
        assert Message.__tablename__ == "messages"

    def test_has_tenant_id(self):
        columns = {c.name for c in Message.__table__.columns}
        assert "tenant_id" in columns

    def test_message_statuses_cover_full_lifecycle(self):
        statuses = [s.value for s in MessageStatus]
        assert "queued" in statuses
        assert "sent" in statuses
        assert "delivered" in statuses
        assert "opened" in statuses
        assert "replied" in statuses
        assert "failed" in statuses
        assert "bounced" in statuses

    def test_composite_indexes_exist(self):
        index_names = {idx.name for idx in Message.__table__.indexes}
        assert "ix_messages_tenant_status" in index_names
        assert "ix_messages_tenant_contact" in index_names
        assert "ix_messages_tenant_channel_direction" in index_names


class TestReplySuggestionModel:
    def test_classification_enum(self):
        classifications = [c.value for c in ReplyClassification]
        assert "interested" in classifications
        assert "price_inquiry" in classifications
        assert "sample_request" in classifications
        assert "meeting_request" in classifications
        assert "not_interested" in classifications
        assert "auto_reply" in classifications
        assert "out_of_office" in classifications


class TestPipelineModel:
    def test_stage_table_name(self):
        assert PipelineStage.__tablename__ == "pipeline_stages"

    def test_opportunity_table_name(self):
        assert PipelineOpportunity.__tablename__ == "pipeline_opportunities"

    def test_opportunity_source_enum(self):
        assert OpportunitySource.discovery.value == "discovery"
        assert OpportunitySource.campaign.value == "campaign"
        assert OpportunitySource.manual.value == "manual"


class TestAgentTaskModel:
    def test_table_name(self):
        assert AgentTask.__tablename__ == "agent_tasks"

    def test_task_types(self):
        types = [t.value for t in AgentTaskType]
        assert "buyer_discovery" in types
        assert "company_research" in types
        assert "contact_enrichment" in types
        assert "message_compose" in types
        assert "reply_suggest" in types

    def test_task_statuses(self):
        statuses = [s.value for s in AgentTaskStatus]
        assert "pending" in statuses
        assert "running" in statuses
        assert "completed" in statuses
        assert "failed" in statuses


class TestAllTablesHaveTenantId:
    """Critical multi-tenancy test: every table except tenants must have tenant_id."""

    EXEMPT_TABLES = {"tenants"}
    # Tables scoped through parent FK rather than direct tenant_id
    PARENT_SCOPED_TABLES = {"campaign_steps", "contact_list_members"}
    # System-wide tables (not tenant-scoped by design)
    SYSTEM_TABLES = {"allowed_emails", "ports", "commodity_references"}

    def test_tenant_scoping(self):
        for mapper in Base.registry.mappers:
            model = mapper.class_
            table_name = model.__tablename__
            columns = {c.name for c in model.__table__.columns}
            if table_name in self.EXEMPT_TABLES:
                assert "tenant_id" not in columns, f"{table_name} should NOT have tenant_id"
            elif table_name in self.PARENT_SCOPED_TABLES or table_name in self.SYSTEM_TABLES:
                pass  # scoped through parent FK or system-wide by design
            else:
                assert "tenant_id" in columns, f"{table_name} MUST have tenant_id for multi-tenancy"


class TestAllTablesHaveTimestamps:
    """Every table must have created_at and updated_at."""

    def test_timestamps(self):
        for mapper in Base.registry.mappers:
            model = mapper.class_
            table_name = model.__tablename__
            columns = {c.name for c in model.__table__.columns}
            assert "created_at" in columns, f"{table_name} missing created_at"
            assert "updated_at" in columns or table_name in {
                "message_events", "activity_log", "credit_transactions",
                "contact_list_members", "pipeline_stages",
            }, f"{table_name} missing updated_at"


class TestAllTablesHaveUUIDPrimaryKey:
    """Every table must use UUID primary keys."""

    def test_uuid_pks(self):
        for mapper in Base.registry.mappers:
            model = mapper.class_
            pk_cols = model.__table__.primary_key.columns
            for col in pk_cols:
                assert "UUID" in str(col.type) or "uuid" in str(col.type).lower(), (
                    f"{model.__tablename__}.{col.name} must use UUID primary key"
                )
