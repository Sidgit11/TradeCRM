"""Whitelist model — controls who can access the platform."""
import uuid
from typing import Optional

from sqlalchemy import Boolean, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AllowedEmail(Base):
    __tablename__ = "allowed_emails"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
