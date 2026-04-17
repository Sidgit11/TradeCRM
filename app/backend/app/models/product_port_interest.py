"""ProductPortInterest — maps buyers/sellers to products and ports with provenance."""
from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Numeric, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import InterestRole, InterestSource, ConfidenceLevel, InterestStatus


class ProductPortInterest(Base):
    __tablename__ = "product_port_interests"
    __table_args__ = (
        Index("ix_ppi_tenant", "tenant_id"),
        Index("ix_ppi_company", "company_id"),
        Index("ix_ppi_contact", "contact_id"),
        Index("ix_ppi_product", "product_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )

    # Attachment — one of company or contact
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=True,
    )
    contact_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=True,
    )

    # Core: which product from tenant catalog
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False,
    )
    variety_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_varieties.id", ondelete="SET NULL"), nullable=True,
    )
    grade_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_grades.id", ondelete="SET NULL"), nullable=True,
    )

    # Ports
    destination_port_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id", ondelete="SET NULL"), nullable=True,
    )
    origin_port_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id", ondelete="SET NULL"), nullable=True,
    )

    # Role
    role: Mapped[InterestRole] = mapped_column(
        Enum(InterestRole, name="interest_role"), default=InterestRole.buyer,
    )

    # Provenance
    source: Mapped[InterestSource] = mapped_column(
        Enum(InterestSource, name="interest_source"), default=InterestSource.manual,
    )
    confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True, default=1.0)
    confidence_level: Mapped[Optional[ConfidenceLevel]] = mapped_column(
        Enum(ConfidenceLevel, name="confidence_level"), nullable=True, default=ConfidenceLevel.high,
    )
    evidence: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # User state
    status: Mapped[InterestStatus] = mapped_column(
        Enum(InterestStatus, name="interest_status"), default=InterestStatus.suggested,
    )
    confirmed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    company = relationship("Company")
    contact = relationship("Contact")
    product = relationship("Product")
    variety = relationship("ProductVariety")
    grade = relationship("ProductGrade")
    destination_port = relationship("Port", foreign_keys=[destination_port_id])
    origin_port = relationship("Port", foreign_keys=[origin_port_id])
