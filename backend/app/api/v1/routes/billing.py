"""
Admin billing endpoints — Phase 6 SaaS monetization.

GET   /admin/billing/plans   — list all available plan definitions
GET   /admin/billing/summary — current plan + platform usage + limit flags
PATCH /admin/billing/plan    — update the admin user's plan_tier (no Stripe)

plan_tier is stored on the users table.  Changing it here is a direct DB
write — no payment processing.  Stripe integration is a future phase.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.plans import PLANS, PlanTier, get_plan
from app.billing.usage_meter import usage_meter
from app.core.deps import get_db, require_admin

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
    admin=Depends(require_admin),
) -> Dict[str, Any]:
    """Return all plan definitions (Free / Pro / Team).

    Plans are sourced directly from billing/plans.py — no DB query needed.
    """
    raw_tier = getattr(admin, "plan_tier", None) or "free"
    return {
        "plans": [_plan_to_dict(p) for p in PLANS.values()],
        "current_plan": raw_tier,
        "assignment_source": "db",
    }


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class UpdatePlanRequest(BaseModel):
    plan_tier: str  # "free" | "pro" | "team"


# ---------------------------------------------------------------------------
# PATCH /plan
# ---------------------------------------------------------------------------

@router.patch(
    "/plan",
    summary="Update the admin user's billing plan tier (no Stripe)",
)
async def update_billing_plan(
    body: UpdatePlanRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Directly update the authenticated admin's plan_tier in the DB.

    No payment processing — dev/demo endpoint only.
    Stripe subscription management is the next phase.
    """
    try:
        new_tier = PlanTier(body.plan_tier.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid plan_tier '{body.plan_tier}'. Must be one of: free, pro, team",
        )

    from sqlalchemy import text as sa_text

    old_tier = getattr(admin, "plan_tier", "free") or "free"

    await db.execute(
        sa_text("UPDATE users SET plan_tier = :tier WHERE id = :uid"),
        {"tier": new_tier.value, "uid": admin.id},
    )

    # Audit — record billing event
    from app.models.billing_event import BillingEvent
    event_type = "plan_activated" if old_tier == "free" and new_tier.value != "free" else "plan_changed"
    db.add(BillingEvent(
        id=str(uuid.uuid4()),
        user_id=admin.id,
        event_type=event_type,
        old_tier=old_tier,
        new_tier=new_tier.value,
        subscription_status=getattr(admin, "subscription_status", "none") or "none",
        details={"source": "admin_ui", "demo_mode": True},
    ))
    await db.commit()

    logger.info(
        "Plan updated | user_id=%s old=%s new=%s",
        admin.id,
        old_tier,
        new_tier.value,
    )
    plan = get_plan(new_tier)
    return {
        "updated": True,
        "plan_tier": new_tier.value,
        "plan_detail": _plan_to_dict(plan),
    }


@router.get(
    "/summary",
    summary="Platform billing summary — current plan, usage, and limit flags",
)
async def get_billing_summary(
    admin=Depends(require_admin),
) -> Dict[str, Any]:
    """Return current plan, usage counters, and limit-warning flags.

    current_plan is read from the authenticated admin user's plan_tier column.
    Falls back to "free" if the field is missing or null (safe for any existing row).

    Usage is platform-wide (sum of all in-memory user counters).
    The in-memory meter resets on restart; a DB-backed meter is the next step.
    """
    raw_tier = getattr(admin, "plan_tier", None) or "free"
    try:
        current_tier = PlanTier(raw_tier)
    except ValueError:
        current_tier = PlanTier.FREE
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
            "plan_assignment": "db",        # plan_tier stored on users table
            "note": (
                "Plan tier is DB-backed (users.plan_tier). "
                "Usage metering is in-memory (resets on restart). "
                "Stripe billing is the next phase."
            ),
        },
        "available_plans": [_plan_to_dict(p) for p in PLANS.values()],
        "subscription": {
            "status": getattr(admin, "subscription_status", "none") or "none",
            "current_period_end": (
                getattr(admin, "current_period_end", None).isoformat()
                if getattr(admin, "current_period_end", None) else None
            ),
        },
    }


# ---------------------------------------------------------------------------
# GET /status  — lightweight subscription status (no usage counters)
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    summary="Subscription status for the authenticated admin",
)
async def get_billing_status(
    admin=Depends(require_admin),
) -> Dict[str, Any]:
    """Return the current subscription lifecycle status for this admin user.

    Lighter than /summary — returns only plan tier and subscription fields.
    Useful for header badges and gate checks without fetching full usage data.
    """
    raw_tier = getattr(admin, "plan_tier", None) or "free"
    try:
        current_tier = PlanTier(raw_tier)
    except ValueError:
        current_tier = PlanTier.FREE

    return {
        "plan_tier": current_tier.value,
        "plan_display": get_plan(current_tier).display_name,
        "subscription_status": getattr(admin, "subscription_status", "none") or "none",
        "current_period_end": (
            getattr(admin, "current_period_end", None).isoformat()
            if getattr(admin, "current_period_end", None) else None
        ),
        "stripe_enabled": False,
    }


# ---------------------------------------------------------------------------
# GET /events  — billing event log (preferred name; /history kept as alias)
# ---------------------------------------------------------------------------

@router.get(
    "/events",
    summary="Recent billing events for the authenticated admin (read-only)",
)
async def get_billing_events(
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> Dict[str, Any]:
    """Return the most recent billing lifecycle events for this user.

    Canonical endpoint.  /history is kept as an alias for backwards compatibility.
    """
    from app.models.billing_event import BillingEvent

    result = await db.execute(
        select(BillingEvent)
        .where(BillingEvent.user_id == admin.id)
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


# ---------------------------------------------------------------------------
# GET /history  — alias kept for backwards compatibility with existing api.ts
# ---------------------------------------------------------------------------

@router.get(
    "/history",
    summary="Recent billing events for the authenticated admin (read-only)",
    include_in_schema=False,
)
async def get_billing_history(
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 20,
) -> Dict[str, Any]:
    """Alias of GET /events — kept for backwards compatibility."""
    return await get_billing_events(admin=admin, db=db, limit=limit)


# ---------------------------------------------------------------------------
# POST /checkout-session  (stub — Stripe not yet enabled)
# ---------------------------------------------------------------------------

class CheckoutSessionRequest(BaseModel):
    plan_tier: str  # "pro" | "team"


@router.post(
    "/checkout-session",
    summary="Create a Stripe checkout session (stub — returns 503 until Stripe is configured)",
)
async def create_checkout_session(
    body: CheckoutSessionRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Stripe checkout session endpoint — NOT yet active.

    When Stripe is configured (STRIPE_SECRET_KEY env var set), this endpoint
    will create a real Checkout Session and return the redirect URL.

    For now it records the intent as a billing_event and returns a clear
    "not enabled" response so the UI can show an appropriate message.
    """
    try:
        PlanTier(body.plan_tier.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid plan_tier '{body.plan_tier}'",
        )

    # Record the checkout intent for audit purposes
    from app.models.billing_event import BillingEvent
    db.add(BillingEvent(
        id=str(uuid.uuid4()),
        user_id=admin.id,
        event_type="checkout_requested",
        old_tier=getattr(admin, "plan_tier", "free") or "free",
        new_tier=body.plan_tier.lower(),
        subscription_status=getattr(admin, "subscription_status", "none") or "none",
        details={"stripe_enabled": False, "requested_tier": body.plan_tier.lower()},
    ))
    await db.commit()

    logger.info(
        "Checkout session requested (stub) | user_id=%s tier=%s",
        admin.id, body.plan_tier,
    )

    return {
        "enabled": False,
        "checkout_url": None,
        "message": (
            "Stripe billing is not yet active. "
            "Use PATCH /admin/billing/plan to assign a plan tier directly (demo mode). "
            "This request has been logged as a billing event."
        ),
        "next_step": "Configure STRIPE_SECRET_KEY and implement webhook handlers to enable live checkout.",
    }
