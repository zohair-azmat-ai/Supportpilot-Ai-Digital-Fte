"""User SQLAlchemy model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """Represents an application user (customer or admin)."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum("customer", "admin", name="user_role", native_enum=False),
        nullable=False,
        default="customer",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Phase 6 — SaaS billing tier for this account.
    # Allowed values: "free" | "pro" | "team". server_default backfills existing rows.
    plan_tier: Mapped[str] = mapped_column(
        String(50), nullable=False, default="free", server_default="free"
    )
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
    conversations: Mapped[list["Conversation"]] = relationship(  # noqa: F821
        "Conversation",
        back_populates="user",
        foreign_keys="Conversation.user_id",
        lazy="select",
    )
    tickets: Mapped[list["Ticket"]] = relationship(  # noqa: F821
        "Ticket",
        back_populates="user",
        foreign_keys="Ticket.user_id",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} role={self.role}>"
