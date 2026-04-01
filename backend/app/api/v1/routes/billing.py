"""
Admin billing endpoints — Phase 6 SaaS monetization.

GET /admin/billing/plans   — list all available plan definitions
GET /admin/billing/summary — current plan + platform usage + limit flags

NOTE: current_plan defaults to "free" — workspace plan assignment is a
future step (Stripe integration).  The response shape is already structured
so callers can swap "free" for a real plan lookup with no API change.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends

from app.billing.plans import PLANS, PlanTier, get_plan
from app.billing.usage_meter import usage_meter
from app.core.deps import require_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/billing", tags=["Billing"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _plan_to_dict(plan) -> Dict[str, Any]:
    """Serialise a Plan dataclass to a JSON-safe dict."""
    return {
        "tier": plan.tier.value,
        "display_name": plan.display_name,
        "monthly_message_limit": plan.monthly_message_limit,
        "monthly_ticket_limit": plan.monthly_ticket_limit,
        "max_agents": plan.max_agents,
        "whatsapp_enabled": plan.whatsapp_enabled,
        "email_enabled": plan.email_enabled,
        "analytics_enabled": plan.analytics_enabled,
        "multi_agent_enabled": plan.multi_agent_enabled,
        "sla_minutes": plan.sla_minutes,
        "soft_limit_pct": plan.soft_limit_pct,
        "features": list(plan.features),
    }


def _usage_counter(used: int, limit: int, soft_pct: float) -> Dict[str, Any]:
    """Build a usage counter dict with warning flags."""
    if limit == -1:
        # Unlimited plan
        return {
            "used": used,
            "limit": -1,
            "pct": 0.0,
            "soft_warning": False,
            "hard_blocked": False,
            "unlimited": True,
        }
    pct = round((used / limit) * 100, 1) if limit > 0 else 0.0
    soft_threshold = int(limit * soft_pct)
    return {
        "used": used,
        "limit": limit,
        "pct": pct,
        "soft_warning": used >= soft_threshold and used < limit,
        "hard_blocked": used >= limit,
        "unlimited": False,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get(
    "/plans",
    summary="List all available billing plans",
)
async def get_billing_plans(
    _admin=Depends(require_admin),
) -> Dict[str, Any]:
    """Return all plan definitions (Free / Pro / Team).

    Plans are sourced directly from billing/plans.py — no DB query needed.
    """
    return {
        "plans": [_plan_to_dict(p) for p in PLANS.values()],
        "current_plan": "free",   # temporary default — replace with real lookup
        "assignment_source": "default",  # "default" | "stripe" | "manual"
    }


@router.get(
    "/summary",
    summary="Platform billing summary — current plan, usage, and limit flags",
)
async def get_billing_summary(
    _admin=Depends(require_admin),
) -> Dict[str, Any]:
    """Return current plan, usage counters, and limit-warning flags.

    Temporary assumption: current_plan = "free" until workspace plan
    assignment is implemented (Stripe phase).

    Usage is platform-wide (sum of all in-memory user counters).
    The in-memory meter resets on restart; a DB-backed meter is the next step.
    """
    current_tier = PlanTier.FREE   # temporary default
    plan = get_plan(current_tier)

    # Sum all in-memory user counters for a platform-wide view
    all_usage = list(usage_meter._usage.values())
    total_messages = sum(u.message_count for u in all_usage)
    total_tickets  = sum(u.ticket_count  for u in all_usage)

    messages_counter = _usage_counter(
        total_messages, plan.monthly_message_limit, plan.soft_limit_pct
    )
    tickets_counter = _usage_counter(
        total_tickets, plan.monthly_ticket_limit, plan.soft_limit_pct
    )

    # Next suggested plan
    tier_order = [PlanTier.FREE, PlanTier.PRO, PlanTier.TEAM]
    current_idx = tier_order.index(current_tier)
    next_plan_tier = tier_order[current_idx + 1] if current_idx + 1 < len(tier_order) else None
    next_plan = _plan_to_dict(get_plan(next_plan_tier)) if next_plan_tier else None

    return {
        "current_plan": plan.tier.value,
        "current_plan_display": plan.display_name,
        "current_plan_detail": _plan_to_dict(plan),
        "usage": {
            "messages": messages_counter,
            "tickets": tickets_counter,
        },
        "next_plan": next_plan,
        "monetization_status": {
            "usage_metering_live": True,
            "stripe_enabled": False,
            "plan_assignment": "default",   # "default" | "stripe" | "manual"
            "note": (
                "Usage metering is live (in-memory, resets on restart). "
                "DB-backed metering and Stripe billing are the next phase."
            ),
        },
        "available_plans": [_plan_to_dict(p) for p in PLANS.values()],
    }
