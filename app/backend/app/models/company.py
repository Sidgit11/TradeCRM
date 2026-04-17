from typing import Optional

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import CompanySource, EnrichmentStatus


class Company(Base):
    __tablename__ = "companies"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )

    # Core info
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    address: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    website: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Business classification
    company_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # importer / distributor / manufacturer / broker / retailer / agent / re-exporter / end_user / other
    company_size: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # small / medium / large / enterprise
    year_established: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    number_of_employees: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # "1-10" / "11-50" / "51-200" / "201-500" / "500+"
    annual_revenue_usd: Mapped[Optional[float]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    annual_trade_value_usd: Mapped[Optional[float]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    # Actual trade value from shipment data — what they import/export annually
    registration_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # IEC (India), EORI (EU), EIN (US), etc.

    # Trade intelligence
    commodities: Mapped[dict] = mapped_column(JSON, default=list, server_default="[]")
    # What they buy — e.g. ["Black Pepper", "Turmeric"]
    target_industries: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Industries their buyers belong to — e.g. ["Grinders", "F&B", "Retail", "Industrial"]
    preferred_origins: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # Countries they source from — e.g. ["India", "Vietnam"]
    preferred_incoterms: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    preferred_payment_terms: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    certifications_required: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # e.g. ["Organic", "Fair Trade", "BRC", "ISO 22000"]
    destination_ports: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # e.g. ["Rotterdam", "Hamburg"]

    # Volume & history
    import_volume_annual: Mapped[Optional[float]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    # Annual import volume in MT
    shipment_frequency: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # monthly / quarterly / biannual / annual / ad-hoc
    last_shipment_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Banking & payment (critical for LC/TT)
    bank_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    bank_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bank_swift_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Tax & legal
    tax_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Social & web
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    social_media: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # e.g. {"twitter": "...", "facebook": "..."}

    # Trade references & intelligence
    known_suppliers: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # e.g. ["Olam", "McCormick"] — other suppliers they work with
    trade_references: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # e.g. [{"name": "...", "company": "...", "phone": "..."}]

    # CRM fields
    rating: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # hot / warm / cold
    tags: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[CompanySource] = mapped_column(
        Enum(CompanySource, name="company_source"), default=CompanySource.manual, server_default="manual",
    )

    # System-tracked
    first_contact_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_inquiries: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_deals_won: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    total_revenue: Mapped[Optional[float]] = mapped_column(Numeric(precision=15, scale=2), nullable=True)

    # Enrichment
    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        Enum(EnrichmentStatus, name="enrichment_status"), default=EnrichmentStatus.not_enriched, server_default="not_enriched",
    )
    enrichment_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Numeric(precision=3, scale=2), nullable=True)

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    contacts = relationship("Contact", back_populates="company")
