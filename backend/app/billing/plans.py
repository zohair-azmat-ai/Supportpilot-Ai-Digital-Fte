"""
Plan definitions for SupportPilot SaaS tiers.

Free  — individual / evaluation, hard message cap
Pro   — small teams, higher limits, priority support
Team  — organisations, unlimited messages, SLA guarantees

These are the source-of-truth plan configs.  Stripe price IDs will be
added here when billing integration is activated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PlanTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"


@dataclass(frozen=True)
class Plan:
    """Defines the capabilities and limits for a billing tier."""

    tier: PlanTier
    display_name: str
    monthly_message_limit: int          # -1 = unlimited
    monthly_ticket_limit: int           # -1 = unlimited
    max_agents: int                     # concurrent AI agent calls
    whatsapp_enabled: bool
    email_enabled: bool
    analytics_enabled: bool
    multi_agent_enabled: bool           # Phase 6 specialist routing
    sla_minutes: Optional[int]          # first-response SLA, None = no SLA
    # Soft-limit threshold — warn when usage reaches this % of hard limit
    soft_limit_pct: float = 0.80
    # Stripe price ID — populated when Stripe integration is activated
    stripe_price_id: Optional[str] = None
    features: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Plan catalogue
# ---------------------------------------------------------------------------

PLANS: dict[PlanTier, Plan] = {
    PlanTier.FREE: Plan(
        tier=PlanTier.FREE,
        display_name="Free",
        monthly_message_limit=200,
        monthly_ticket_limit=50,
        max_agents=1,
        whatsapp_enabled=False,
        email_enabled=False,
        analytics_enabled=False,
        multi_agent_enabled=False,
        sla_minutes=None,
        features=[
            "AI chat (web only)",
            "Basic ticket management",
            "Conversation history (last 30 days)",
        ],
    ),
    PlanTier.PRO: Plan(
        tier=PlanTier.PRO,
        display_name="Pro",
        monthly_message_limit=2_000,
        monthly_ticket_limit=500,
        max_agents=3,
        whatsapp_enabled=True,
        email_enabled=True,
        analytics_enabled=True,
        multi_agent_enabled=False,
        sla_minutes=60,
        features=[
            "Everything in Free",
            "WhatsApp + Email channels",
            "Analytics dashboard",
            "1-hour first-response SLA",
            "Priority support",
        ],
    ),
    PlanTier.TEAM: Plan(
        tier=PlanTier.TEAM,
        display_name="Team",
        monthly_message_limit=-1,
        monthly_ticket_limit=-1,
        max_agents=10,
        whatsapp_enabled=True,
        email_enabled=True,
        analytics_enabled=True,
        multi_agent_enabled=True,
        sla_minutes=15,
        features=[
            "Everything in Pro",
            "Unlimited messages & tickets",
            "Multi-agent routing (Phase 6)",
            "15-min first-response SLA",
            "Dedicated workspace isolation",
            "Custom escalation rules",
        ],
    ),
}


def get_plan(tier: str | PlanTier) -> Plan:
    """Return the Plan for a given tier string or enum.

    Defaults to Free if the tier is unrecognised.
    """
    if isinstance(tier, str):
        try:
            tier = PlanTier(tier.lower())
        except ValueError:
            tier = PlanTier.FREE
    return PLANS.get(tier, PLANS[PlanTier.FREE])
