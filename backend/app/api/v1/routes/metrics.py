"""
Metrics API endpoints — AI agent performance and analytics.

Endpoints:
  GET /metrics/overview     — Platform-wide aggregate metrics
  GET /metrics/channels     — Per-channel breakdown
  GET /metrics/escalations  — Recent escalations list

All endpoints require admin role.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_admin_user
from app.repositories.agent_metrics import AgentMetricsRepository
from app.schemas.metrics import (
    ChannelMetricsResponse,
    EscalationsResponse,
    EventsOverviewResponse,
    MetricsOverviewResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "/overview",
    response_model=MetricsOverviewResponse,
    summary="Platform-wide AI performance metrics",
)
async def get_metrics_overview(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_admin_user),
) -> MetricsOverviewResponse:
    """
    Return aggregated AI agent performance metrics across all interactions.

    Includes:
    - Total interaction count
    - Average confidence score
    - Average response time in milliseconds
    - Escalation rate and absolute count
    - Ticket creation rate
    - Average tools called per run
    - Average iterations per run
    - Top 5 detected intents with counts
    """
    repo = AgentMetricsRepository(db)
    stats = await repo.get_aggregate_stats()
    return MetricsOverviewResponse(**stats)


@router.get(
    "/channels",
    response_model=ChannelMetricsResponse,
    summary="Per-channel AI performance breakdown",
)
async def get_channel_metrics(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_admin_user),
) -> ChannelMetricsResponse:
    """
    Return AI agent performance metrics broken down by channel.

    Channels: web, email, whatsapp (and null/unknown for older records).
    """
    repo = AgentMetricsRepository(db)
    data = await repo.get_channel_stats()
    return ChannelMetricsResponse(**data)


@router.get(
    "/escalations",
    response_model=EscalationsResponse,
    summary="Recent escalations and escalation analysis",
)
async def get_escalations(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_admin_user),
) -> EscalationsResponse:
    """
    Return recent escalation records with reasons and context.

    Useful for:
    - Human agent review queue
    - Escalation pattern analysis
    - Agent performance tuning

    Args:
        limit: Maximum number of recent escalations to return (default 50, max 200).
    """
    limit = min(limit, 200)
    repo = AgentMetricsRepository(db)
    data = await repo.get_escalation_stats(limit=limit)
    return EscalationsResponse(**data)


@router.get(
    "/events",
    response_model=EventsOverviewResponse,
    summary="Platform-wide event log analytics",
)
async def get_events_overview(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(get_current_admin_user),
) -> EventsOverviewResponse:
    """
    Return analytics derived from the system_events log.

    Includes:
    - Total events logged across all types
    - Per event-type counts
    - Per-channel breakdown
    - Top intents from AI response events
    - Convenience counters for key event types (forms submitted, messages,
      AI responses, tickets, escalations, similar issues, duplicates prevented)
    """
    from app.repositories.system_event import SystemEventRepository

    repo = SystemEventRepository(db)
    data = await repo.get_events_overview()
    return EventsOverviewResponse(**data)
