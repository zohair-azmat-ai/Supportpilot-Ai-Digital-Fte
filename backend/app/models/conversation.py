"""Conversation SQLAlchemy model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import DateTime, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Conversation(Base):
    """Represents a support conversation thread."""

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(
        Enum("web", "email", "whatsapp", name="conversation_channel", native_enum=False),
        nullable=False,
        default="web",
    )
    status: Mapped[str] = mapped_column(
        Enum("active", "closed", "escalated", name="conversation_status", native_enum=False),
        nullable=False,
        default="active",
    )
    subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    user: Mapped["User"] = relationship(  # noqa: F821
        "User",
        back_populates="conversations",
        foreign_keys=[user_id],
        lazy="select",
    )
    messages: Mapped[List["Message"]] = relationship(  # noqa: F821
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
        lazy="select",
    )
    tickets: Mapped[List["Ticket"]] = relationship(  # noqa: F821
        "Ticket",
        back_populates="conversation",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} status={self.status} user_id={self.user_id}>"
