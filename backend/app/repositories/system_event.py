"""SystemEvent repository — write and query the platform event log."""

from __future__ import annotations

from typing import Any, Dict, List

from sqlalchemy import func, select

from app.models.system_event import SystemEvent
from app.repositories.base import BaseRepository


class SystemEventRepository(BaseRepository[SystemEvent]):
    """Data access layer for the SystemEvent model."""

    model = SystemEvent

    async def log(self, data_dict: dict) -> SystemEvent:
        """Append a new system event record."""
        return await self.create(data_dict)

    async def get_event_counts(self) -> List[Dict[str, Any]]:
        """Return count of each event_type across all time, descending."""
        result = await self.db.execute(
            select(
                SystemEvent.event_type,
                func.count(SystemEvent.id).label("count"),
            )
            .group_by(SystemEvent.event_type)
            .order_by(func.count(SystemEvent.id).desc())
        )
        return [{"event_type": r.event_type, "count": r.count} for r in result]

    async def get_events_overview(self) -> Dict[str, Any]:
        """Return platform-wide event analytics."""
        # Total events
        total_result = await self.db.execute(select(func.count(SystemEvent.id)))
        total = int(total_result.scalar_one_or_none() or 0)

        # Per-type counts
        counts = await self.get_event_counts()

        # Per-channel breakdown
        channel_result = await self.db.execute(
            select(
                SystemEvent.channel,
                func.count(SystemEvent.id).label("count"),
            )
            .where(SystemEvent.channel.isnot(None))
            .group_by(SystemEvent.channel)
            .order_by(func.count(SystemEvent.id).desc())
        )
        channel_breakdown = [
            {"channel": r.channel, "count": r.count}
            for r in channel_result
        ]

        # Top intents from ai_response_generated events
        intent_result = await self.db.execute(
            select(
                SystemEvent.intent,
                func.count(SystemEvent.id).label("count"),
            )
            .where(SystemEvent.intent.isnot(None))
            .group_by(SystemEvent.intent)
            .order_by(func.count(SystemEvent.id).desc())
            .limit(10)
        )
        intent_breakdown = [
            {"intent": r.intent, "count": r.count}
            for r in intent_result
        ]

        counts_by_type = {c["event_type"]: c["count"] for c in counts}

        return {
            "total_events": total,
            "event_type_counts": counts,
            "channel_breakdown": channel_breakdown,
            "intent_breakdown": intent_breakdown,
            "support_forms_submitted": counts_by_type.get("support_form_submitted", 0),
            "messages_received": counts_by_type.get("message_received", 0),
            "ai_responses_generated": counts_by_type.get("ai_response_generated", 0),
            "tickets_created": counts_by_type.get("ticket_created", 0),
            "tickets_updated": counts_by_type.get("ticket_updated", 0),
            "escalations": counts_by_type.get("issue_escalated", 0),
            "similar_issues_detected": counts_by_type.get("similar_issue_detected", 0),
            "duplicate_tickets_prevented": counts_by_type.get(
                "duplicate_ticket_prevented", 0
            ),
        }
