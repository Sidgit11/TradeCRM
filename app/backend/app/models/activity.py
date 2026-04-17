from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import (
    ActorType,
    AgentTaskStatus,
    AgentTaskType,
    CreditActionType,
)


class ActivityLog(Base):
    __tablename__ = "activity_log"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_type: Mapped[ActorType] = mapped_column(
        Enum(ActorType, name="actor_type"), nullable=False
    )
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)


class CreditTransaction(Base):
    __tablename__ = "credit_transactions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action_type: Mapped[CreditActionType] = mapped_column(
        Enum(CreditActionType, name="credit_action_type"), nullable=False
    )
    credits_consumed: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )


class AgentTask(Base):
    __tablename__ = "agent_tasks"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_type: Mapped[AgentTaskType] = mapped_column(
        Enum(AgentTaskType, name="agent_task_type"), nullable=False
    )
    status: Mapped[AgentTaskStatus] = mapped_column(
        Enum(AgentTaskStatus, name="agent_task_status"),
        default=AgentTaskStatus.pending,
        server_default="pending",
    )
    steps: Mapped[dict] = mapped_column(JSON, default=list, server_default="[]")
    current_step_index: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    input_data: Mapped[dict] = mapped_column(JSON, default=dict, server_default="{}")
    output_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    credits_consumed: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0"
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    creator = relationship("User")
