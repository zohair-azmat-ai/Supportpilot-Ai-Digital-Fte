"""AgentMetrics repository — persistence and analytics queries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import Float, func, select

from app.models.agent_metrics import AgentMetrics
from app.repositories.base import BaseRepository


class AgentMetricsRepository(BaseRepository[AgentMetrics]):
    """Data access layer for the AgentMetrics model."""

    model = AgentMetrics

    async def record(self, data_dict: dict) -> AgentMetrics:
        """Persist a new agent metrics record after an agent run."""
        return await self.create(data_dict)

    async def get_by_conversation(self, conversation_id: str) -> List[AgentMetrics]:
        """Return all metrics records for a specific conversation (oldest first)."""
        result = await self.db.execute(
            select(AgentMetrics)
            .where(AgentMetrics.conversation_id == conversation_id)
            .order_by(AgentMetrics.created_at.asc())
        )
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # Platform-wide aggregate stats
    # ------------------------------------------------------------------

    async def get_aggregate_stats(self) -> Dict[str, Any]:
        """Compute platform-wide AI performance statistics.

        Returns a dict matching the MetricsOverviewResponse schema:
            total_interactions, avg_confidence, avg_response_ms,
            escalation_rate, escalation_count, ticket_creation_rate,
            avg_tools_per_run, avg_iterations, top_intents
        """
        # --- Total count and scalar averages ---
        agg_result = await self.db.execute(
            select(
                func.count(AgentMetrics.id).label("total"),
                func.avg(AgentMetrics.confidence_score).label("avg_confidence"),
                func.avg(AgentMetrics.response_time_ms).label("avg_response_ms"),
                func.avg(AgentMetrics.iterations).label("avg_iterations"),
            )
        )
        row = agg_result.mappings().first()
        total = int(row["total"] or 0)

        # --- Escalation count ---
        esc_result = await self.db.execute(
            select(func.count(AgentMetrics.id)).where(
                AgentMetrics.was_escalated == True  # noqa: E712
            )
        )
        escalation_count = int(esc_result.scalar_one_or_none() or 0)

        # --- Ticket creation count ---
        ticket_result = await self.db.execute(
            select(func.count(AgentMetrics.id)).where(
                AgentMetrics.ticket_created == True  # noqa: E712
            )
        )
        ticket_count = int(ticket_result.scalar_one_or_none() or 0)

        # --- Average tools called (JSON list length via Python — SQLAlchemy-portable) ---
        tools_result = await self.db.execute(
            select(AgentMetrics.tools_called).where(AgentMetrics.tools_called.isnot(None))
        )
        all_tool_lists = [r[0] for r in tools_result.all() if isinstance(r[0], list)]
        avg_tools = (
            sum(len(t) for t in all_tool_lists) / len(all_tool_lists)
            if all_tool_lists else 0.0
        )

        # --- Top 5 intents ---
        intents_result = await self.db.execute(
            select(
                AgentMetrics.intent_detected,
                func.count(AgentMetrics.id).label("cnt"),
            )
            .where(AgentMetrics.intent_detected.isnot(None))
            .group_by(AgentMetrics.intent_detected)
            .order_by(func.count(AgentMetrics.id).desc())
            .limit(5)
        )
        top_intents = [
            {"intent": r.intent_detected, "count": r.cnt}
            for r in intents_result
        ]

        return {
            "total_interactions": total,
            "avg_confidence": round(float(row["avg_confidence"] or 0.0), 4),
            "avg_response_ms": round(float(row["avg_response_ms"] or 0.0), 1),
            "escalation_rate": round(escalation_count / total, 4) if total else 0.0,
            "escalation_count": escalation_count,
            "ticket_creation_rate": round(ticket_count / total, 4) if total else 0.0,
            "avg_tools_per_run": round(avg_tools, 2),
            "avg_iterations": round(float(row["avg_iterations"] or 0.0), 2),
            "top_intents": top_intents,
        }

    # ------------------------------------------------------------------
    # Per-channel breakdown
    # ------------------------------------------------------------------

    async def get_channel_stats(self) -> Dict[str, Any]:
        """Compute per-channel performance breakdown.

        Returns a dict matching the ChannelMetricsResponse schema.
        """
        channel_result = await self.db.execute(
            select(
                AgentMetrics.channel,
                func.count(AgentMetrics.id).label("interaction_count"),
                func.avg(AgentMetrics.confidence_score).label("avg_confidence"),
                func.avg(AgentMetrics.response_time_ms).label("avg_response_ms"),
                func.sum(
                    func.cast(AgentMetrics.was_escalated, Float)
                ).label("escalation_sum"),
            )
            .group_by(AgentMetrics.channel)
            .order_by(func.count(AgentMetrics.id).desc())
        )

        channels = []
        total = 0
        for row in channel_result.mappings():
            count = int(row["interaction_count"] or 0)
            esc_sum = int(row["escalation_sum"] or 0)
            total += count
            channels.append({
                "channel": row["channel"] or "unknown",
                "interaction_count": count,
                "avg_confidence": round(float(row["avg_confidence"] or 0.0), 4),
                "avg_response_ms": round(float(row["avg_response_ms"] or 0.0), 1),
                "escalation_count": esc_sum,
                "escalation_rate": round(esc_sum / count, 4) if count else 0.0,
            })

        return {
            "channels": channels,
            "total_interactions": total,
        }

    # ------------------------------------------------------------------
    # Escalation detail
    # ------------------------------------------------------------------

    async def get_escalation_stats(self, limit: int = 50) -> Dict[str, Any]:
        """Return recent escalation records and aggregate escalation stats.

        Returns a dict matching the EscalationsResponse schema.
        """
        # Total and rate
        total_result = await self.db.execute(select(func.count(AgentMetrics.id)))
        total = int(total_result.scalar_one_or_none() or 0)

        esc_result = await self.db.execute(
            select(func.count(AgentMetrics.id)).where(
                AgentMetrics.was_escalated == True  # noqa: E712
            )
        )
        esc_total = int(esc_result.scalar_one_or_none() or 0)

        # Recent escalation records
        recent_result = await self.db.execute(
            select(AgentMetrics)
            .where(AgentMetrics.was_escalated == True)  # noqa: E712
            .order_by(AgentMetrics.created_at.desc())
            .limit(limit)
        )
        recent = recent_result.scalars().all()

        return {
            "total_escalations": esc_total,
            "escalation_rate": round(esc_total / total, 4) if total else 0.0,
            "recent_escalations": [
                {
                    "conversation_id": r.conversation_id,
                    "channel": r.channel,
                    "intent_detected": r.intent_detected,
                    "escalation_reason": r.escalation_reason,
                    "confidence_score": r.confidence_score,
                    "response_time_ms": r.response_time_ms,
                    "created_at": r.created_at.isoformat(),
                }
                for r in recent
            ],
        }
