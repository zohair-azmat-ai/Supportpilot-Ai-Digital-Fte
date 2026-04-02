"""
Customer-facing billing endpoints.

GET   /billing/summary  — current user's plan, per-user usage, subscription status
GET   /billing/events   — current user's billing event history
POST  /billing/checkout-session — real Stripe checkout (falls back to stub when not configured)

These mirror the /admin/billing/* routes but are accessible to any authenticated
user (not just admins) and return per-user usage instead of platform-wide totals.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.plans import PLANS, PlanTier, get_plan
from app.billing.stripe_helpers import create_checkout_session as _stripe_checkout
from app.billing.usage_meter import usage_meter
from app.core.deps import get_current_active_user, get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Customer Billing"])


# ---------------------------------------------------------------------------
# Helpers (duplicated from admin billing to keep routes self-contained)
# ---------------------------------------------------------------------------

def _plan_to_dict(plan) -> Dict[str, Any]:
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
    if limit == -1:
        return {"used": used, "limit": -1, "pct": 0.0,
                "soft_warning": False, "hard_blocked": False, "unlimited": True}
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
    "/summary",
    summary="Current user's plan, per-user usage, and subscription status",
)
async def get_customer_billing_summary(
    current_user=Depends(get_current_active_user),
) -> Dict[str, Any]:
    """Return the authenticated user's plan and usage — no admin role required."""
    raw_tier = getattr(current_user, "plan_tier", None) or "free"
    try:
        current_tier = PlanTier(raw_tier)
    except ValueError:
        current_tier = PlanTier.FREE
    plan = get_plan(current_tier)

    # Per-user usage counters from the in-memory meter
    user_usage = await usage_meter.get_usage(current_user.id)
    msg_used    = user_usage.message_count
    ticket_used = user_usage.ticket_count

    messages_counter = _usage_counter(msg_used, plan.monthly_message_limit, plan.soft_limit_pct)
    tickets_counter  = _usage_counter(ticket_used, plan.monthly_ticket_limit, plan.soft_limit_pct)

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
        "monetization_status": {"stripe_enabled": False, "demo_mode": True},
        "available_plans": [_plan_to_dict(p) for p in PLANS.values()],
        "subscription": {
            "status": getattr(current_user, "subscription_status", "none") or "none",
            "current_period_end": (
                getattr(current_user, "current_period_end", None).isoformat()
                if getattr(current_user, "current_period_end", None) else None
            ),
        },
    }


@router.get(
    "/events",
    summary="Current user's billing event history",
)
async def get_customer_billing_events(
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> Dict[str, Any]:
    """Return billing events recorded for the current user (plan changes, checkout attempts)."""
    from app.models.billing_event import BillingEvent

    result = await db.execute(
        select(BillingEvent)
        .where(BillingEvent.user_id == current_user.id)
        .order_by(BillingEvent.created_at.desc())
        .limit(max(1, min(limit, 100)))
    )
    events = result.scalars().all()

    return {
        "events": [
            {
                "id": e.id,
                "event_type": e.event_type,
                "old_tier": e.old_tier,
                "new_tier": e.new_tier,
                "subscription_status": e.subscription_status,
                "details": e.details,
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ],
        "total": len(events),
    }


class CheckoutRequest(BaseModel):
    plan_tier: str


@router.post(
    "/checkout-session",
    summary="Create a Stripe checkout session (live when STRIPE_SECRET_KEY is set)",
)
async def customer_checkout_session(
    body: CheckoutRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a Stripe Checkout Session for the selected plan.

    Live when ``STRIPE_SECRET_KEY`` is configured; falls back to stub otherwise.
    Returns ``400`` for the free plan, ``422`` for an unrecognised tier.
    """
    try:
        new_tier = PlanTier(body.plan_tier.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid plan_tier '{body.plan_tier}'. Must be one of: free, pro, team",
        )

    if new_tier == PlanTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot create a checkout session for the Free plan.",
        )

    from app.models.billing_event import BillingEvent
    db.add(BillingEvent(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        event_type="checkout_requested",
        old_tier=getattr(current_user, "plan_tier", "free") or "free",
        new_tier=new_tier.value,
        subscription_status=getattr(current_user, "subscription_status", "none") or "none",
        details={"source": "customer_ui", "requested_at": datetime.now(timezone.utc).isoformat()},
    ))
    await db.commit()

    try:
        result = await _stripe_checkout(current_user, new_tier, db)
    except Exception:
        logger.exception("Customer checkout session creation failed | user_id=%s", current_user.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Stripe checkout session. Please try again.",
        )

    logger.info(
        "Customer checkout | user_id=%s tier=%s enabled=%s",
        current_user.id, new_tier.value, result.get("enabled"),
    )
    return result
