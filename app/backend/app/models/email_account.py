"""Connected email accounts — supports multiple Gmail/Outlook accounts per tenant."""
import uuid
from typing import Optional

from sqlalchemy import Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EmailAccount(Base):
    """A connected email account (Gmail or Outlook) for a tenant."""
    __tablename__ = "email_accounts"
    __table_args__ = (
        Index("ix_email_accounts_tenant_id", "tenant_id"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False,
    )
    email_address: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # "gmail" or "outlook"
    display_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    token_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)  # encrypted in production
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    connected_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    last_sync_at: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
