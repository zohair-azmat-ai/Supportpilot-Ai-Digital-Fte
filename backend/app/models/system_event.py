"""
SystemEvent model — append-only log of platform events for analytics.

One record per significant action:
  message_received, ai_response_generated, ticket_created, ticket_updated,
  issue_escalated, similar_issue_detected, duplicate_ticket_prevented,
  support_form_submitted
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemEvent(Base):
    """Append-only audit/analytics log of platform events."""

    __tablename__ = "system_events"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    event_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    conversation_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    ticket_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True,
    )
    channel: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    intent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    urgency: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return (
            f"<SystemEvent id={self.id} type={self.event_type} "
            f"conversation={self.conversation_id}>"
        )
