from typing import Optional

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import OpportunitySource


class PipelineStage(Base):
    __tablename__ = "pipeline_stages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[str] = mapped_column(String(7), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class PipelineOpportunity(Base):
    __tablename__ = "pipeline_opportunities"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )

    # Linked entities
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True,
    )
    lead_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_stages.id", ondelete="CASCADE"), nullable=False, index=True,
    )

    # Deal identity
    display_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, unique=True, index=True)
    # Human-readable short ID e.g. "TRAD-0001"
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # Human-readable deal name e.g. "500MT Black Pepper - Rotterdam"

    # Product details
    commodity: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True,
    )
    grade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    # Deal details
    quantity_mt: Mapped[Optional[float]] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    target_price: Mapped[Optional[float]] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    # Buyer's target price per MT
    our_price: Mapped[Optional[float]] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    # Our offered price per MT
    competitor_price: Mapped[Optional[float]] = mapped_column(Numeric(precision=10, scale=2), nullable=True)
    # Known competitor quote per MT
    estimated_value_usd: Mapped[Optional[float]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")
    incoterms: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Shipping & logistics
    origin_port_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id", ondelete="SET NULL"), nullable=True,
    )
    destination_port_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id", ondelete="SET NULL"), nullable=True,
    )
    container_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # 20ft / 40ft / 40ft_hc
    number_of_containers: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    target_shipment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    shipping_line: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Quality & packaging
    packaging_requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # e.g. "25kg PP bags, palletized"
    quality_specifications: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # e.g. {"moisture": "<12%", "admixture": "<1%", "defective": "<3%"}

    # Forecasting
    expected_close_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    probability: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    follow_up_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Sample tracking
    sample_sent: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    sample_sent_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    sample_approved: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    sample_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Outcome
    loss_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Metadata
    source: Mapped[OpportunitySource] = mapped_column(
        Enum(OpportunitySource, name="opportunity_source"), default=OpportunitySource.manual, server_default="manual",
    )
    source_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    value: Mapped[Optional[float]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    assigned_to: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    documents: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # System
    last_activity_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    company = relationship("Company")
    contact = relationship("Contact")
    stage = relationship("PipelineStage")
    assignee = relationship("User")
