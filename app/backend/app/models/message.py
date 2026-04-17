from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import (
    ChannelType,
    MessageDirection,
    MessageEventType,
    MessageStatus,
)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("ix_messages_tenant_status", "tenant_id", "status"),
        Index("ix_messages_tenant_contact", "tenant_id", "contact_id"),
        Index("ix_messages_tenant_channel_direction", "tenant_id", "channel", "direction"),
    )

    campaign_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="SET NULL"),
        nullable=True,
    )
    campaign_step_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaign_steps.id", ondelete="SET NULL"),
        nullable=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contacts.id", ondelete="CASCADE"),
        nullable=False,
    )
    sent_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, name="channel_type", create_type=False), nullable=False
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection, name="message_direction"), nullable=False
    )
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[MessageStatus] = mapped_column(
        Enum(MessageStatus, name="message_status"),
        default=MessageStatus.queued,
        server_default="queued",
    )
    external_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    personalization_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    opened_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    clicked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    replied_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failed_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    contact = relationship("Contact")
    campaign = relationship("Campaign")
    events = relationship("MessageEvent", back_populates="message", lazy="selectin")


class MessageEvent(Base):
    __tablename__ = "message_events"

    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[MessageEventType] = mapped_column(
        Enum(MessageEventType, name="message_event_type"), nullable=False
    )
    event_data: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")

    message = relationship("Message", back_populates="events")
