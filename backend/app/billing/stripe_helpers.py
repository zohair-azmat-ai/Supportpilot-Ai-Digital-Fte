"""Shared Stripe API helpers used by both admin and customer billing routes.

All Stripe SDK calls are synchronous; they are wrapped with
``anyio.to_thread.run_sync`` so they don't block the async event loop.

Graceful degradation:
  When STRIPE_SECRET_KEY is empty or not set, every function falls back to
  stub behaviour (no HTTP calls to Stripe, no exceptions raised) so the app
  continues to run in demo mode without any Stripe configuration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import anyio
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.plans import PlanTier
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _stripe_configured() -> bool:
    """Return True when a real Stripe secret key is present in the environment."""
    return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith("sk_"))


def _get_stripe():
    """Return the stripe module with api_key set, or raise if not configured."""
    import stripe  # local import so missing package only fails at call time
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def get_stripe_price_id(tier: PlanTier) -> Optional[str]:
    """Look up the Stripe price ID for the given plan tier from env vars."""
    if tier == PlanTier.PRO:
        return settings.STRIPE_PRICE_ID_PRO or None
    if tier == PlanTier.TEAM:
        return settings.STRIPE_PRICE_ID_TEAM or None
    return None


def price_id_to_plan_tier(price_id: str) -> Optional[str]:
    """Reverse-map a Stripe price ID back to a plan tier string."""
    if settings.STRIPE_PRICE_ID_PRO and price_id == settings.STRIPE_PRICE_ID_PRO:
        return PlanTier.PRO.value
    if settings.STRIPE_PRICE_ID_TEAM and price_id == settings.STRIPE_PRICE_ID_TEAM:
        return PlanTier.TEAM.value
    return None


# ---------------------------------------------------------------------------
# Customer management
# ---------------------------------------------------------------------------

async def get_or_create_stripe_customer(user: Any, db: AsyncSession) -> str:
    """Return the existing Stripe customer ID or create a new one.

    The customer ID is persisted to ``users.stripe_customer_id`` so that
    future checkouts reuse the same Stripe customer object.

    Raises:
        stripe.StripeError — propagated from the Stripe API on failure.
    """
    existing = getattr(user, "stripe_customer_id", None)
    if existing:
        return existing

    stripe = _get_stripe()
    customer = await anyio.to_thread.run_sync(
        lambda: stripe.Customer.create(
            email=user.email,
            name=user.name,
            metadata={"user_id": user.id},
        )
    )
    customer_id: str = customer.id

    await db.execute(
        sa_text("UPDATE users SET stripe_customer_id = :cid WHERE id = :uid"),
        {"cid": customer_id, "uid": user.id},
    )
    # Commit so the customer_id is durable even if the session is later rolled back
    await db.commit()

    logger.info("Created Stripe customer | user_id=%s customer_id=%s", user.id, customer_id)
    return customer_id


# ---------------------------------------------------------------------------
# Checkout session
# ---------------------------------------------------------------------------

async def create_checkout_session(
    user: Any,
    tier: PlanTier,
    db: AsyncSession,
) -> Dict[str, Any]:
    """Create a real Stripe Checkout Session (subscription mode).

    Falls back to stub response when Stripe is not configured.

    Returns a dict with keys:
      - ``enabled``     bool   — True when a real session was created
      - ``checkout_url`` str | None
      - ``session_id``  str | None
      - ``message``     str    — human-readable status
    """
    if not _stripe_configured():
        logger.info(
            "Stripe not configured — returning stub response for user_id=%s tier=%s",
            user.id, tier.value,
        )
        return {
            "enabled": False,
            "checkout_url": None,
            "session_id": None,
            "message": (
                f"Stripe is not yet configured. "
                f"Your interest in the {tier.value.title()} plan has been noted!"
            ),
        }

    price_id = get_stripe_price_id(tier)
    if not price_id:
        return {
            "enabled": False,
            "checkout_url": None,
            "session_id": None,
            "message": (
                f"No Stripe price ID configured for the {tier.value} plan. "
                "Set STRIPE_PRICE_ID_PRO / STRIPE_PRICE_ID_TEAM in the environment."
            ),
        }

    stripe = _get_stripe()

    try:
        customer_id = await get_or_create_stripe_customer(user, db)

        session = await anyio.to_thread.run_sync(
            lambda: stripe.checkout.Session.create(
                customer=customer_id,
                client_reference_id=user.id,  # used in webhook to find the user
                mode="subscription",
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=settings.STRIPE_SUCCESS_URL,
                cancel_url=settings.STRIPE_CANCEL_URL,
                metadata={"user_id": user.id, "plan_tier": tier.value},
            )
        )
    except Exception as exc:
        logger.exception(
            "Stripe checkout session creation failed | user_id=%s tier=%s",
            user.id, tier.value,
        )
        raise exc

    logger.info(
        "Stripe checkout session created | user_id=%s tier=%s session_id=%s",
        user.id, tier.value, session.id,
    )
    return {
        "enabled": True,
        "checkout_url": session.url,
        "session_id": session.id,
        "message": "Checkout session created. Redirecting to Stripe…",
    }


# ---------------------------------------------------------------------------
# Subscription period helpers
# ---------------------------------------------------------------------------

def unix_to_datetime(ts: Optional[int]) -> Optional[datetime]:
    """Convert a Unix timestamp to a UTC-aware datetime, or return None."""
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc)
