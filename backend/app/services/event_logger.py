"""Centralized event logger — fire-and-forget, never crashes the caller."""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class EventLogger:
    """
    Centralized service for logging platform events to the system_events table.

    All logging is fire-and-forget: failures are swallowed and logged as
    warnings so they never affect the caller's response.

    Event type constants
    --------------------
    MESSAGE_RECEIVED            — user message stored in DB
    AI_RESPONSE_GENERATED       — AI agent produced a reply
    TICKET_CREATED              — new support ticket created
    TICKET_UPDATED              — existing ticket status/fields changed
    ISSUE_ESCALATED             — conversation escalated to human
    SIMILAR_ISSUE_DETECTED      — repeat/duplicate issue found in history
    DUPLICATE_TICKET_PREVENTED  — create_ticket skipped (existing ticket found)
    SUPPORT_FORM_SUBMITTED      — public support form submitted
    """

    MESSAGE_RECEIVED = "message_received"
    AI_RESPONSE_GENERATED = "ai_response_generated"
    TICKET_CREATED = "ticket_created"
    TICKET_UPDATED = "ticket_updated"
    ISSUE_ESCALATED = "issue_escalated"
    SIMILAR_ISSUE_DETECTED = "similar_issue_detected"
    DUPLICATE_TICKET_PREVENTED = "duplicate_ticket_prevented"
    SUPPORT_FORM_SUBMITTED = "support_form_submitted"

    async def log(
        self,
        db: AsyncSession,
        event_type: str,
        *,
        user_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        ticket_id: Optional[str] = None,
        channel: Optional[str] = None,
        intent: Optional[str] = None,
        priority: Optional[str] = None,
        sentiment: Optional[str] = None,
        urgency: Optional[str] = None,
        confidence: Optional[float] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Persist a system event record.

        Safe to call from any async context — all exceptions are caught and
        logged as warnings so they never propagate to the caller.
        """
        try:
            from app.repositories.system_event import SystemEventRepository

            repo = SystemEventRepository(db)
            await repo.log({
                "event_type": event_type,
                "user_id": user_id,
                "conversation_id": conversation_id,
                "ticket_id": ticket_id,
                "channel": channel,
                "intent": intent,
                "priority": priority,
                "sentiment": sentiment,
                "urgency": urgency,
                "confidence": confidence,
                "details": details,
            })
        except Exception as exc:
            logger.warning("EventLogger.log failed for %s: %s", event_type, exc)


event_logger = EventLogger()
