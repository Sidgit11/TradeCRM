from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ReplyClassification, SuggestionStatus


class ReplySuggestion(Base):
    __tablename__ = "reply_suggestions"

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
    classification: Mapped[ReplyClassification] = mapped_column(
        Enum(ReplyClassification, name="reply_classification"), nullable=False
    )
    suggested_reply_text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(
        Numeric(precision=3, scale=2), nullable=False
    )
    status: Mapped[SuggestionStatus] = mapped_column(
        Enum(SuggestionStatus, name="suggestion_status"),
        default=SuggestionStatus.pending,
        server_default="pending",
    )
    edited_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    actioned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    message = relationship("Message")
