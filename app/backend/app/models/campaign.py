from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import CampaignStatus, CampaignType, ChannelType, StepCondition


class Campaign(Base):
    __tablename__ = "campaigns"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[CampaignType] = mapped_column(
        Enum(CampaignType, name="campaign_type"), nullable=False
    )
    status: Mapped[CampaignStatus] = mapped_column(
        Enum(CampaignStatus, name="campaign_status"),
        default=CampaignStatus.draft,
        server_default="draft",
    )
    contact_list_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contact_lists.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    settings: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")

    steps = relationship("CampaignStep", back_populates="campaign", order_by="CampaignStep.step_number", lazy="selectin")
    contact_list = relationship("ContactList")
    creator = relationship("User")


class CampaignStep(Base):
    __tablename__ = "campaign_steps"

    campaign_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[ChannelType] = mapped_column(
        Enum(ChannelType, name="channel_type"), nullable=False
    )
    delay_days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    condition: Mapped[StepCondition] = mapped_column(
        Enum(StepCondition, name="step_condition"),
        default=StepCondition.always,
        server_default="always",
    )
    template_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    whatsapp_template_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    subject_template: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    message_template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("message_templates.id", ondelete="SET NULL"), nullable=True,
    )

    campaign = relationship("Campaign", back_populates="steps")
    message_template = relationship("MessageTemplate")
