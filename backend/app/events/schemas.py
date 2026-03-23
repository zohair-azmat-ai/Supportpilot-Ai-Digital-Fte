"""Pydantic v2 event payload schemas for SupportPilot AI event bus."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict


class BaseEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    event_id: str  # uuid4
    event_type: str
    timestamp: datetime
    channel: str  # 'web' | 'email' | 'whatsapp'


class SupportMessageEvent(BaseEvent):
    """Published when a customer sends a chat message."""

    event_type: str = "support.message"
    conversation_id: str
    user_id: str
    content: str
    conversation_history: list[dict]  # [{sender_type, content}]


class SupportFormEvent(BaseEvent):
    """Published when a web support form is submitted."""

    event_type: str = "support.form"
    name: str
    email: str
    subject: str
    message: str
    category: str
    priority: str


class TicketCreatedEvent(BaseEvent):
    """Published when a ticket is created."""

    event_type: str = "ticket.created"
    ticket_id: str
    user_id: str
    title: str
    category: str
    priority: str


class EscalationEvent(BaseEvent):
    """Published when an AI escalation is triggered."""

    event_type: str = "support.escalation"
    conversation_id: str
    ticket_id: str | None
    reason: str
    intent: str


class MetricsEvent(BaseEvent):
    """Published after each AI interaction for analytics."""

    event_type: str = "metrics.interaction"
    conversation_id: str
    intent: str
    confidence: float
    response_time_ms: float
    was_escalated: bool
    model_used: str


def make_event(cls: type[BaseEvent], **kwargs: Any) -> BaseEvent:
    """Factory function to create any event with auto-generated id and timestamp."""
    return cls(
        event_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        channel=kwargs.pop("channel", "web"),
        **kwargs,
    )
