"""MessageTemplate model — reusable email/WhatsApp message templates."""
from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TemplateChannel, TemplateCategory


class MessageTemplate(Base):
    __tablename__ = "message_templates"
    __table_args__ = (
        Index("ix_message_templates_tenant_channel", "tenant_id", "channel"),
        Index("ix_message_templates_tenant_category", "tenant_id", "category"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[TemplateChannel] = mapped_column(
        Enum(TemplateChannel, name="template_channel"), nullable=False,
    )
    category: Mapped[TemplateCategory] = mapped_column(
        Enum(TemplateCategory, name="template_category"), default=TemplateCategory.custom,
    )

    # Email-only
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Body
    body: Mapped[str] = mapped_column(Text, nullable=False)
    body_format: Mapped[str] = mapped_column(String(10), default="plain", server_default="plain")

    # Variables detected in body/subject
    variables: Mapped[Optional[list]] = mapped_column(JSON, default=list, server_default="[]")

    # Metadata
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    ai_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Tracking
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    creator = relationship("User")
