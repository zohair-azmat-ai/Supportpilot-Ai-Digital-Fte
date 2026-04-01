"""Pydantic schemas for the metrics API endpoints."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class IntentCount(BaseModel):
    intent: str
    count: int


class SentimentCount(BaseModel):
    sentiment: str
    count: int


class UrgencyCount(BaseModel):
    urgency: str
    count: int


class EscalationCauseCount(BaseModel):
    cause: str
    count: int


class RoutedAgentCount(BaseModel):
    agent: str
    count: int


class ConversationAgent(BaseModel):
    conversation_id: str
    routed_agent: str


class RoutingMapResponse(BaseModel):
    """Latest routed agent per recent conversation."""
    routing: List[ConversationAgent]


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
    sentiment_breakdown: List[SentimentCount] = []
    urgency_distribution: List[UrgencyCount] = []
    escalation_cause_breakdown: List[EscalationCauseCount] = []
    similar_issue_count: int = 0
    similar_issue_rate: float = 0.0
    routing_breakdown: List[RoutedAgentCount] = []


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


class EventTypeCount(BaseModel):
    event_type: str
    count: int


class ChannelEventCount(BaseModel):
    channel: str
    count: int


class IntentEventCount(BaseModel):
    intent: str
    count: int


class EventsOverviewResponse(BaseModel):
    """Platform-wide event log analytics."""
    total_events: int
    event_type_counts: List[EventTypeCount]
    channel_breakdown: List[ChannelEventCount]
    intent_breakdown: List[IntentEventCount]
    support_forms_submitted: int = 0
    messages_received: int = 0
    ai_responses_generated: int = 0
    tickets_created: int = 0
    tickets_updated: int = 0
    escalations: int = 0
    similar_issues_detected: int = 0
    duplicate_tickets_prevented: int = 0
