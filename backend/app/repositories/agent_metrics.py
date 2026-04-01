"""AgentMetrics repository — persistence and analytics queries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import case, func, select, text

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

        # --- Sentiment breakdown ---
        sentiment_result = await self.db.execute(
            select(
                AgentMetrics.sentiment,
                func.count(AgentMetrics.id).label("cnt"),
            )
            .where(AgentMetrics.sentiment.isnot(None))
            .group_by(AgentMetrics.sentiment)
            .order_by(func.count(AgentMetrics.id).desc())
        )
        sentiment_breakdown = [
            {"sentiment": r.sentiment, "count": r.cnt}
            for r in sentiment_result
        ]

        # --- Urgency distribution ---
        urgency_result = await self.db.execute(
            select(
                AgentMetrics.urgency,
                func.count(AgentMetrics.id).label("cnt"),
            )
            .where(AgentMetrics.urgency.isnot(None))
            .group_by(AgentMetrics.urgency)
            .order_by(func.count(AgentMetrics.id).desc())
        )
        urgency_distribution = [
            {"urgency": r.urgency, "count": r.cnt}
            for r in urgency_result
        ]

        # --- Similar issue detection rate ---
        sim_result = await self.db.execute(
            select(func.count(AgentMetrics.id)).where(
                AgentMetrics.similar_issue_detected == True  # noqa: E712
            )
        )
        similar_issue_count = int(sim_result.scalar_one_or_none() or 0)

        # --- Escalation cause breakdown ---
        cause_result = await self.db.execute(
            select(
                AgentMetrics.escalation_cause,
                func.count(AgentMetrics.id).label("cnt"),
            )
            .where(AgentMetrics.escalation_cause.isnot(None))
            .group_by(AgentMetrics.escalation_cause)
            .order_by(func.count(AgentMetrics.id).desc())
        )
        escalation_cause_breakdown = [
            {"cause": r.escalation_cause, "count": r.cnt}
            for r in cause_result
        ]

        routing_breakdown = await self.get_routing_stats()

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
            "sentiment_breakdown": sentiment_breakdown,
            "urgency_distribution": urgency_distribution,
            "escalation_cause_breakdown": escalation_cause_breakdown,
            "similar_issue_count": similar_issue_count,
            "similar_issue_rate": round(similar_issue_count / total, 4) if total else 0.0,
            "routing_breakdown": routing_breakdown,
        }

    # ------------------------------------------------------------------
    # Specialist routing breakdown
    # ------------------------------------------------------------------

    async def get_routing_stats(self) -> List[Dict[str, Any]]:
        """Return per-specialist-agent interaction counts, ordered by volume."""
        result = await self.db.execute(
            select(
                AgentMetrics.routed_agent,
                func.count(AgentMetrics.id).label("cnt"),
            )
            .where(AgentMetrics.routed_agent.isnot(None))
            .group_by(AgentMetrics.routed_agent)
            .order_by(func.count(AgentMetrics.id).desc())
        )
        return [
            {"agent": r.routed_agent, "count": r.cnt}
            for r in result
        ]

    async def get_per_conversation_routing(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Return the most recent routed_agent for each conversation (newest first).

        Uses a subquery to pick the latest metric row per conversation.
        """
        subq = (
            select(
                AgentMetrics.conversation_id,
                func.max(AgentMetrics.created_at).label("max_ts"),
            )
            .group_by(AgentMetrics.conversation_id)
            .subquery()
        )
        result = await self.db.execute(
            select(AgentMetrics.conversation_id, AgentMetrics.routed_agent)
            .join(
                subq,
                (AgentMetrics.conversation_id == subq.c.conversation_id)
                & (AgentMetrics.created_at == subq.c.max_ts),
            )
            .where(AgentMetrics.routed_agent.isnot(None))
            .order_by(AgentMetrics.created_at.desc())
            .limit(limit)
        )
        return [
            {"conversation_id": r.conversation_id, "routed_agent": r.routed_agent}
            for r in result
        ]

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
                    case((AgentMetrics.was_escalated == True, 1), else_=0)  # noqa: E712
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
