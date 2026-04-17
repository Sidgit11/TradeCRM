"""Shipment model — cached trade shipment records for company intelligence."""
from typing import Optional

import uuid
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ShipmentDirection


class Shipment(Base):
    __tablename__ = "shipments"
    __table_args__ = (
        Index("ix_shipments_tenant_company", "tenant_id", "company_id"),
        Index("ix_shipments_company_date", "company_id", "shipment_date"),
        Index("ix_shipments_hs", "hs_code"),
        UniqueConstraint("tenant_id", "source_id", name="uq_shipments_source"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
    )
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)
    source_provider: Mapped[str] = mapped_column(String(50), default="tradecrm_internal")

    shipment_date: Mapped[date] = mapped_column(Date, nullable=False)
    direction: Mapped[ShipmentDirection] = mapped_column(
        Enum(ShipmentDirection, name="shipment_direction", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
    )

    commodity_text: Mapped[str] = mapped_column(String(255), nullable=False)
    hs_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    origin_country: Mapped[str] = mapped_column(String(100), nullable=False)
    destination_country: Mapped[str] = mapped_column(String(100), nullable=False)

    origin_port_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id", ondelete="SET NULL"), nullable=True,
    )
    destination_port_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id", ondelete="SET NULL"), nullable=True,
    )
    origin_port_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    destination_port_text: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    volume_mt: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    unit_price_usd_per_mt: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    value_usd: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)

    trade_partner_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    trade_partner_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    trade_partner_company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True,
    )

    matched_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"), nullable=True,
    )
    match_confidence: Mapped[Optional[float]] = mapped_column(Numeric(3, 2), nullable=True)

    raw: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    company = relationship("Company", foreign_keys=[company_id])
    origin_port = relationship("Port", foreign_keys=[origin_port_id])
    destination_port = relationship("Port", foreign_keys=[destination_port_id])
    matched_product = relationship("Product")
