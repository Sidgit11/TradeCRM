"""Product catalog, pricing, ports, and freight models."""
import uuid
from typing import Optional
from datetime import date

from sqlalchemy import (
    Boolean, Date, ForeignKey, Index, Integer,
    Numeric, String, Text, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Port(Base):
    """Global port directory — shared across tenants."""
    __tablename__ = "ports"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    __table_args__ = (
        Index("ix_ports_country", "country"),
    )


class Product(Base):
    """A product in a tenant's catalog. e.g. Black Pepper, Vanilla Sticks."""
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_tenant_id", "tenant_id"),
        UniqueConstraint("tenant_id", "name", "origin_country", name="uq_product_tenant_name_origin"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_country: Mapped[str] = mapped_column(String(100), nullable=False)
    hs_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Trade-specific fields
    default_loading_port_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id"), nullable=True,
    )
    shelf_life_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    certifications: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # ["FSSAI", "Organic", "Fair Trade"]
    aliases: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # ["black pepper", "kali mirch"] — for AI matching

    # Container capacity — user-defined per product (varies by commodity density)
    capacity_20ft_mt: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)  # e.g. 18.0
    capacity_40ft_mt: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)  # e.g. 26.0
    capacity_40ft_hc_mt: Mapped[Optional[float]] = mapped_column(Numeric(6, 2), nullable=True)  # e.g. 28.0

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    varieties = relationship("ProductVariety", back_populates="product", lazy="selectin")
    default_loading_port = relationship("Port")


class ProductVariety(Base):
    """A variety/type under a product. e.g. Malabar, Tellicherry."""
    __tablename__ = "product_varieties"
    __table_args__ = (
        Index("ix_product_varieties_product_id", "product_id"),
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    product = relationship("Product", back_populates="varieties")
    grades = relationship("ProductGrade", back_populates="variety", lazy="selectin")


class ProductGrade(Base):
    """A grade/quality under a variety. e.g. 500GL, 550GL, TGSEB."""
    __tablename__ = "product_grades"
    __table_args__ = (
        Index("ix_product_grades_variety_id", "variety_id"),
    )

    variety_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_varieties.id", ondelete="CASCADE"), nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Specifications — flexible JSON for any quality parameters
    specifications: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # e.g. {"moisture": "12%", "density": "550 g/l", "admixture": "<1%"}

    # Packaging
    packaging_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # e.g. "PP bags", "Jute bags", "Carton", "Bulk"
    packaging_weight_kg: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    # e.g. 25.0 (per bag), 50.0

    # Minimum order
    moq_mt: Mapped[Optional[float]] = mapped_column(Numeric(8, 2), nullable=True)
    # e.g. 1.0 (1 metric ton minimum)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    variety = relationship("ProductVariety", back_populates="grades")


class FobPrice(Base):
    """Daily FOB price for a specific product grade from an origin port."""
    __tablename__ = "fob_prices"
    __table_args__ = (
        Index("ix_fob_prices_tenant_date", "tenant_id", "price_date"),
        Index("ix_fob_prices_grade_id", "grade_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    grade_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("product_grades.id", ondelete="CASCADE"), nullable=False,
    )
    origin_port_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id"), nullable=False,
    )
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    price_usd_per_kg: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    price_usd_per_mt: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    grade = relationship("ProductGrade")
    origin_port = relationship("Port")


class FreightRate(Base):
    """Freight rate from origin port to destination port."""
    __tablename__ = "freight_rates"
    __table_args__ = (
        Index("ix_freight_rates_tenant_id", "tenant_id"),
        Index("ix_freight_rates_ports", "origin_port_id", "destination_port_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    origin_port_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id"), nullable=False,
    )
    destination_port_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id"), nullable=False,
    )
    container_type: Mapped[str] = mapped_column(
        String(20), default="20ft", server_default="20ft",
    )
    rate_usd: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    transit_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_until: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    origin_port = relationship("Port", foreign_keys=[origin_port_id])
    destination_port = relationship("Port", foreign_keys=[destination_port_id])


class TenantDefaults(Base):
    """Per-tenant default settings for trade operations."""
    __tablename__ = "tenant_defaults"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    default_origin_port_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ports.id"), nullable=True,
    )
    default_currency: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")
    default_container_type: Mapped[str] = mapped_column(String(20), default="20ft", server_default="20ft")
    default_payment_terms: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # e.g. "TT Advance", "LC at Sight", "CAD"
    supported_incoterms: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # e.g. ["FOB", "CIF", "CFR", "CnF"]
    custom_settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    default_origin_port = relationship("Port")
