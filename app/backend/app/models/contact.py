from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ContactEnrichmentStatus, ContactSource


class Contact(Base):
    __tablename__ = "contacts"
    __table_args__ = (
        Index("ix_contacts_tenant_email", "tenant_id", "email"),
        Index("ix_contacts_tenant_phone", "tenant_id", "phone"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )

    # Core info
    salutation: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    # Mr / Mrs / Ms / Dr / Prof
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    secondary_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    secondary_phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    whatsapp_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # May differ from phone — e.g. landline vs mobile

    # Location
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Professional info
    company_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="SET NULL"), nullable=True,
    )
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # e.g. "Head of Purchasing", "Managing Director"
    department: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # e.g. "Procurement", "Trading", "Management", "Quality"
    is_decision_maker: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Communication preferences
    preferred_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    preferred_channel: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    # email / whatsapp / phone
    do_not_contact: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Social
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # CRM fields
    tags: Mapped[dict] = mapped_column(JSON, default=list, server_default="[]")
    custom_fields: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source: Mapped[ContactSource] = mapped_column(
        Enum(ContactSource, name="contact_source"), default=ContactSource.manual, server_default="manual",
    )

    # Consent
    opted_in_whatsapp: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    opted_in_email: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    # Tracking
    last_inbound_whatsapp_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_contacted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # System-tracked
    enrichment_status: Mapped[ContactEnrichmentStatus] = mapped_column(
        Enum(ContactEnrichmentStatus, name="contact_enrichment_status"),
        default=ContactEnrichmentStatus.not_enriched, server_default="not_enriched",
    )
    last_interaction_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    first_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    total_interactions: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    company = relationship("Company", back_populates="contacts")


class ContactList(Base):
    __tablename__ = "contact_lists"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    members = relationship("ContactListMember", back_populates="contact_list", lazy="selectin")


class ContactListMember(Base):
    __tablename__ = "contact_list_members"

    contact_list_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contact_lists.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")

    contact_list = relationship("ContactList", back_populates="members")
    contact = relationship("Contact")
