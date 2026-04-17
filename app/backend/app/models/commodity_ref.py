"""Commodity reference data — HS codes, common aliases, default properties."""
from typing import Optional

from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class CommodityReference(Base):
    """Global reference table for commodities — not tenant-scoped."""
    __tablename__ = "commodity_references"
    __table_args__ = (
        Index("ix_commodity_ref_name", "name"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    hs_codes: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # e.g. ["0904.11", "0904.12"] — can be multiple per commodity
    aliases: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    # e.g. ["kali mirch", "piper nigrum", "black pepper whole"]
    category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # e.g. "Spices", "Seafood", "Coffee & Tea"
    default_capacity_20ft_mt: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    default_capacity_40ft_mt: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
