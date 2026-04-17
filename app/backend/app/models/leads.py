"""Inbound leads and personalization preferences models."""
import uuid
from typing import Optional
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer,
    Numeric, String, Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class LeadPreferences(Base):
    """Per-tenant personalization rules for lead classification and reply drafting."""
    __tablename__ = "lead_preferences"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )

    # Classification rules
    ignore_below_qty_mt: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    ignore_countries: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # ["country1", ...]
    auto_non_lead_if_no_catalog_match: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Reply rules
    reply_tone: Mapped[str] = mapped_column(String(20), default="formal", server_default="formal")
    reply_language: Mapped[str] = mapped_column(String(20), default="match_sender", server_default="match_sender")
    include_fob_price: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    include_cfr_quote: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    include_certifications: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    include_moq: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # High-value rules
    high_value_threshold_mt: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    high_value_reply_style: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Custom AI instructions
    custom_reply_instructions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class InboundLead(Base):
    """An email classified by the AI agent — lead or non-lead."""
    __tablename__ = "inbound_leads"
    __table_args__ = (
        Index("ix_inbound_leads_tenant_id", "tenant_id"),
        Index("ix_inbound_leads_thread", "tenant_id", "gmail_thread_id"),
        Index("ix_inbound_leads_status", "tenant_id", "classification", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    email_account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("email_accounts.id", ondelete="CASCADE"), nullable=False,
    )
    gmail_message_id: Mapped[str] = mapped_column(String(100), nullable=False)
    gmail_thread_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Classification
    classification: Mapped[str] = mapped_column(String(20), nullable=False)  # lead | non_lead
    non_lead_reason: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)

    # Sender info (extracted)
    sender_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sender_company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    sender_designation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # CRM match suggestions
    matched_contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True,
    )
    matched_contact_confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)
    matched_company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True,
    )
    matched_company_confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)

    # Email content
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body_preview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    body_full: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    received_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    thread_message_count: Mapped[int] = mapped_column(Integer, default=1, server_default="1")

    # Inquiry details (leads only)
    products_mentioned: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    quantities: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    target_price: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    delivery_terms: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    destination: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    urgency: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    specific_questions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), default="new", server_default="new")
    is_high_value: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True,
    )
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI draft reply (generated on demand)
    draft_reply: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    draft_reply_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
