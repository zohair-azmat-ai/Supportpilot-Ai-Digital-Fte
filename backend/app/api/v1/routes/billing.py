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

from fastapi import Request

from app.billing.plans import PLANS, PlanTier, get_plan
from app.billing.stripe_helpers import (
    _stripe_configured,
    create_checkout_session as _stripe_checkout,
    price_id_to_plan_tier,
    unix_to_datetime,
)
from app.billing.usage_meter import usage_meter
from app.core.config import settings
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
            "stripe_enabled": _stripe_configured(),
            "plan_assignment": "db",        # plan_tier stored on users table
            "note": (
                "Plan tier is DB-backed (users.plan_tier). "
                "Usage metering is in-memory (resets on restart). "
                + (
                    "Stripe billing is live (STRIPE_SECRET_KEY configured)."
                    if _stripe_configured()
                    else "Stripe billing is not yet configured (STRIPE_SECRET_KEY missing)."
                )
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
    summary="Create a Stripe checkout session (live when STRIPE_SECRET_KEY is set)",
)
async def create_checkout_session(
    body: CheckoutSessionRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Create a Stripe Checkout Session for the selected plan.

    When ``STRIPE_SECRET_KEY`` is set in the environment a real Stripe session
    is created and the ``checkout_url`` redirect link is returned.

    When Stripe is not configured the endpoint falls back to stub behaviour:
    it records the intent as a billing event and returns ``enabled: false``.

    Returns ``400`` for the free plan (no checkout needed) and ``422`` for an
    unrecognised tier.
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

    # Always record the checkout intent for audit purposes
    from app.models.billing_event import BillingEvent
    db.add(BillingEvent(
        id=str(uuid.uuid4()),
        user_id=admin.id,
        event_type="checkout_requested",
        old_tier=getattr(admin, "plan_tier", "free") or "free",
        new_tier=new_tier.value,
        subscription_status=getattr(admin, "subscription_status", "none") or "none",
        details={"source": "admin_ui", "requested_tier": new_tier.value},
    ))
    await db.commit()

    try:
        result = await _stripe_checkout(admin, new_tier, db)
    except Exception as exc:
        logger.exception("Checkout session creation failed | user_id=%s", admin.id)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Stripe checkout session. Please try again.",
        ) from exc

    logger.info(
        "Checkout | user_id=%s tier=%s enabled=%s",
        admin.id, new_tier.value, result.get("enabled"),
    )
    return result


# ---------------------------------------------------------------------------
# POST /webhook  — Stripe webhook receiver
# ---------------------------------------------------------------------------

@router.post(
    "/webhook",
    summary="Stripe webhook receiver",
    include_in_schema=False,  # not a user-facing endpoint
)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Receive and verify Stripe webhook events.

    Handled event types:
      - ``checkout.session.completed``    — activate subscription on the user
      - ``customer.subscription.updated`` — sync status / period / tier changes
      - ``customer.subscription.deleted`` — mark subscription as canceled

    Stripe signature is verified using ``STRIPE_WEBHOOK_SECRET``.
    Returns 400 on invalid signature so Stripe knows to retry.
    """
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET is not set — ignoring")
        return {"received": True}

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        import stripe  # local import — missing package only fails here
        stripe.api_key = settings.STRIPE_SECRET_KEY
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except Exception as exc:
        logger.warning("Stripe webhook signature verification failed: %s", exc)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Stripe signature")

    event_type: str = event["type"]
    data_obj = event["data"]["object"]
    logger.info("Stripe webhook | type=%s id=%s", event_type, event.get("id"))

    from app.models.billing_event import BillingEvent
    from app.models.user import User
    from sqlalchemy import select as sa_select, text as sa_text

    # ------------------------------------------------------------------
    # checkout.session.completed
    # ------------------------------------------------------------------
    if event_type == "checkout.session.completed":
        metadata: Dict[str, Any] = data_obj.get("metadata") or {}
        # Prefer client_reference_id (set explicitly at session creation);
        # fall back to metadata.user_id for sessions created before this fix.
        user_id: Optional[str] = (
            data_obj.get("client_reference_id")
            or metadata.get("user_id")
            or None
        )
        stripe_customer_id: str = data_obj.get("customer", "")
        stripe_sub_id: Optional[str] = data_obj.get("subscription")
        plan_tier_value: Optional[str] = metadata.get("plan_tier")

        if not user_id:
            logger.warning(
                "Stripe webhook: no user mapping found in client_reference_id or metadata "
                "| session_id=%s customer=%s — skipping",
                data_obj.get("id"), stripe_customer_id,
            )
            return {"received": True}

        logger.info(
            "Stripe webhook: mapped checkout session to user_id=%s | session_id=%s plan=%s",
            user_id, data_obj.get("id"), plan_tier_value,
        )

        # Update user row
        updates: Dict[str, Any] = {
            "subscription_status": "active",
            "stripe_customer_id": stripe_customer_id,
        }
        if stripe_sub_id:
            updates["stripe_subscription_id"] = stripe_sub_id
        if plan_tier_value:
            updates["plan_tier"] = plan_tier_value

        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["uid"] = user_id
        await db.execute(
            sa_text(f"UPDATE users SET {set_clause} WHERE id = :uid"),
            updates,
        )

        db.add(BillingEvent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            event_type="subscription_activated",
            new_tier=plan_tier_value,
            subscription_status="active",
            details={"stripe_session_id": data_obj.get("id"), "stripe_customer_id": stripe_customer_id},
        ))
        await db.commit()
        logger.info(
            "Stripe webhook: checkout.session.completed applied | user_id=%s plan=%s sub_id=%s",
            user_id, plan_tier_value, stripe_sub_id,
        )

    # ------------------------------------------------------------------
    # customer.subscription.updated
    # ------------------------------------------------------------------
    elif event_type == "customer.subscription.updated":
        stripe_customer_id = data_obj.get("customer", "")
        sub_status: str = data_obj.get("status", "active")
        period_end_ts: Optional[int] = data_obj.get("current_period_end")
        period_end_dt = unix_to_datetime(period_end_ts)

        # Reverse-map price ID to plan tier
        items_data = (data_obj.get("items") or {}).get("data") or []
        price_id = (items_data[0].get("price") or {}).get("id") if items_data else None
        new_plan = price_id_to_plan_tier(price_id) if price_id else None

        result = await db.execute(
            sa_select(User).where(User.stripe_customer_id == stripe_customer_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("subscription.updated: no user found for customer_id=%s", stripe_customer_id)
            return {"received": True}

        updates = {
            "subscription_status": sub_status,
            "stripe_subscription_id": data_obj.get("id"),
        }
        if period_end_dt:
            updates["current_period_end"] = period_end_dt.isoformat()
        if new_plan:
            updates["plan_tier"] = new_plan

        set_clause = ", ".join(f"{k} = :{k}" for k in updates)
        updates["uid"] = user.id
        await db.execute(
            sa_text(f"UPDATE users SET {set_clause} WHERE id = :uid"),
            updates,
        )

        db.add(BillingEvent(
            id=str(uuid.uuid4()),
            user_id=user.id,
            event_type="subscription_updated",
            new_tier=new_plan,
            subscription_status=sub_status,
            details={"stripe_subscription_id": data_obj.get("id"), "price_id": price_id},
        ))
        await db.commit()
        logger.info("subscription.updated processed | user_id=%s status=%s", user.id, sub_status)

    # ------------------------------------------------------------------
    # customer.subscription.deleted
    # ------------------------------------------------------------------
    elif event_type == "customer.subscription.deleted":
        stripe_customer_id = data_obj.get("customer", "")

        result = await db.execute(
            sa_select(User).where(User.stripe_customer_id == stripe_customer_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("subscription.deleted: no user found for customer_id=%s", stripe_customer_id)
            return {"received": True}

        await db.execute(
            sa_text(
                "UPDATE users SET subscription_status = 'canceled', "
                "stripe_subscription_id = NULL, current_period_end = NULL WHERE id = :uid"
            ),
            {"uid": user.id},
        )

        db.add(BillingEvent(
            id=str(uuid.uuid4()),
            user_id=user.id,
            event_type="subscription_canceled",
            old_tier=getattr(user, "plan_tier", None),
            subscription_status="canceled",
            details={"stripe_subscription_id": data_obj.get("id")},
        ))
        await db.commit()
        logger.info("subscription.deleted processed | user_id=%s", user.id)

    else:
        logger.debug("Stripe webhook | unhandled event type=%s — acknowledged", event_type)

    return {"received": True}
