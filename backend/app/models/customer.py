"""
Customer model — CRM-level profile.

Separate from the auth User model. A Customer represents a real-world person
or organisation interacting with the support system. A Customer may or may not
have a corresponding auth User account.

Linked to users via user_id (optional FK).
Linked to CustomerIdentifier for multi-channel identity resolution.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Customer(Base):
    """CRM-level customer profile, independent from the auth User model."""

    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    plan: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        # Examples: 'free', 'pro', 'enterprise'
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
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
    identifiers: Mapped[List["CustomerIdentifier"]] = relationship(
        "CustomerIdentifier",
        back_populates="customer",
        cascade="all, delete-orphan",
        lazy="select",
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name={self.name} plan={self.plan}>"


class CustomerIdentifier(Base):
    """Allows multiple channel-based identities to be associated with a single Customer.

    For example, one customer can have a web identity (email), a WhatsApp identity
    (phone number), and an email identity simultaneously.
    """

    __tablename__ = "customer_identifiers"

    __table_args__ = (
        UniqueConstraint("channel", "value", name="uq_customer_identifier_channel_value"),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    customer_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(
        Enum("web", "email", "whatsapp", name="identifier_channel", native_enum=False),
        nullable=False,
    )
    value: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        # The actual identifier — e.g., an email address, phone number, or session token
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer",
        back_populates="identifiers",
        foreign_keys=[customer_id],
        lazy="select",
    )

    def __repr__(self) -> str:
        return (
            f"<CustomerIdentifier id={self.id} channel={self.channel} "
            f"value={self.value} primary={self.is_primary}>"
        )
