"""Pydantic schemas for the metrics API endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class IntentCount(BaseModel):
    intent: str
    count: int


class MetricsOverviewResponse(BaseModel):
    """Aggregate platform-wide AI performance metrics."""
    total_interactions: int
    avg_confidence: float
    avg_response_ms: float
    escalation_rate: float
    escalation_count: int
    ticket_creation_rate: float
    avg_tools_per_run: float
    avg_iterations: float
    top_intents: List[IntentCount]


class ChannelMetric(BaseModel):
    channel: str
    interaction_count: int
    avg_confidence: float
    avg_response_ms: float
    escalation_count: int
    escalation_rate: float


class ChannelMetricsResponse(BaseModel):
    """Per-channel breakdown of AI agent performance."""
    channels: List[ChannelMetric]
    total_interactions: int


class EscalationRecord(BaseModel):
    conversation_id: str
    channel: Optional[str]
    intent_detected: Optional[str]
    escalation_reason: Optional[str]
    confidence_score: Optional[float]
    response_time_ms: Optional[float]
    created_at: str


class EscalationsResponse(BaseModel):
    """Recent escalations with reasons for human review."""
    total_escalations: int
    escalation_rate: float
    recent_escalations: List[EscalationRecord]
