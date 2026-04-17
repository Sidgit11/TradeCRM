"""CompanyShipmentSummary — precomputed aggregates for O(1) company page rendering."""
from typing import Optional

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TradeRole, ShipmentCadence


class CompanyShipmentSummary(Base):
    __tablename__ = "company_shipment_summaries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "company_id", name="uq_shipment_summary_tenant_company"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True,
    )

    last_refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    data_through_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    source_providers: Mapped[Optional[list]] = mapped_column(JSON, default=list)

    # All-time totals
    total_shipments: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_volume_mt: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    total_value_usd: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)

    # Last 12 months
    shipments_12mo: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    volume_12mo_mt: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)
    value_12mo_usd: Mapped[Optional[float]] = mapped_column(Numeric(18, 2), nullable=True)

    # Inferred
    role: Mapped[Optional[TradeRole]] = mapped_column(
        Enum(TradeRole, name="trade_role"), nullable=True,
    )
    cadence: Mapped[Optional[ShipmentCadence]] = mapped_column(
        Enum(ShipmentCadence, name="shipment_cadence"), nullable=True,
    )
    avg_unit_price_usd_per_mt: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    price_min: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    price_max: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    # Top-N denormalized
    top_partners: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    top_lanes: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    top_commodities: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Monthly series for charts (24 months)
    monthly_series: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    # Catalog match quality
    catalog_match_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    catalog_match_volume_mt: Mapped[Optional[float]] = mapped_column(Numeric(15, 2), nullable=True)

    company = relationship("Company")
