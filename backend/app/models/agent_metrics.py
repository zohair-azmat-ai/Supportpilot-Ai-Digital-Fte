"""
AgentMetrics model — records AI agent performance per interaction.

Stored after every agent run for analytics and monitoring.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentMetrics(Base):
    """Performance and outcome metrics captured after each agent run."""

    __tablename__ = "agent_metrics"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Channel the interaction came in on: 'web', 'email', 'whatsapp'
    channel: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, index=True)
    intent_detected: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    urgency: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    tools_called: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        # Ordered list of tool names invoked during the agent loop
    )
    iterations: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        # Number of reasoning iterations the agent loop executed
    )
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    model_used: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    was_escalated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    escalation_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    ticket_created: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    kb_articles_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        # No updated_at — metrics records are append-only and never modified after creation
    )

    def __repr__(self) -> str:
        return (
            f"<AgentMetrics id={self.id} conversation_id={self.conversation_id} "
            f"intent={self.intent_detected} escalated={self.was_escalated}>"
        )
