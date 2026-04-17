"""WhatsApp message templates — locally managed, synced from Gupshup."""
import uuid
from typing import Optional

from sqlalchemy import ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class WhatsAppTemplate(Base):
    __tablename__ = "whatsapp_templates"
    __table_args__ = (
        Index("ix_wa_templates_tenant", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(50), default="MARKETING", server_default="MARKETING")
    language: Mapped[str] = mapped_column(String(10), default="en", server_default="en")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    variables: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    sample_values: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="approved", server_default="approved")
