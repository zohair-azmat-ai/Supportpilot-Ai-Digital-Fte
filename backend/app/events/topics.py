"""Kafka topic name constants for SupportPilot AI."""

from __future__ import annotations


class Topic:
    WEBFORM_INBOUND = "webform_inbound"
    EMAIL_INBOUND = "email_inbound"
    WHATSAPP_INBOUND = "whatsapp_inbound"
    TICKETS_INCOMING = "tickets_incoming"
    ESCALATIONS = "escalations"
    METRICS = "metrics"


ALL_TOPICS: list[str] = [
    Topic.WEBFORM_INBOUND,
    Topic.EMAIL_INBOUND,
    Topic.WHATSAPP_INBOUND,
    Topic.TICKETS_INCOMING,
    Topic.ESCALATIONS,
    Topic.METRICS,
]
