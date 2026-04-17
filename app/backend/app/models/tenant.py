from typing import Optional

from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PlanType


class Tenant(Base):
    __tablename__ = "tenants"

    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    plan: Mapped[PlanType] = mapped_column(
        Enum(PlanType, name="plan_type"),
        default=PlanType.free_trial, server_default="free_trial", nullable=False,
    )
    commodities: Mapped[dict] = mapped_column(JSON, default=list, server_default="[]")
    target_markets: Mapped[dict] = mapped_column(JSON, default=list, server_default="[]")
    certifications: Mapped[dict] = mapped_column(JSON, default=list, server_default="[]")
    about: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Gupshup WhatsApp
    gupshup_app_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gupshup_app_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    gupshup_app_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    gupshup_api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    whatsapp_phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    whatsapp_status: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    whatsapp_connected_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Email
    sendgrid_api_key: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    email_warmup_state: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    supabase_org_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    users = relationship("User", back_populates="tenant", lazy="selectin")
