"""
Limit enforcement — checks whether a user has reached their plan limits.

Hard limit  → action is blocked; caller must return an error/warning to the user.
Soft limit  → action is allowed but a warning is returned (user should be notified).

Usage:
    from app.billing.limits import check_limits, LimitResult

    result = await check_limits(
        user_id="u123",
        plan_tier="free",
        action="message",
    )
    if result.hard_blocked:
        return {"error": result.message}
    if result.soft_warning:
        # inject warning into AI response or UI notification
        ...
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

from app.billing.plans import PlanTier, get_plan
from app.billing.usage_meter import usage_meter

logger = logging.getLogger(__name__)

Action = Literal["message", "ticket"]


@dataclass
class LimitResult:
    """Result of a limit check."""
    user_id: str
    action: Action
    plan_tier: str
    current_count: int
    limit: int                  # -1 = unlimited
    soft_warning: bool = False
    hard_blocked: bool = False
    message: str = ""


async def check_limits(
    user_id: str,
    plan_tier: str | PlanTier,
    action: Action,
    db=None,
) -> LimitResult:
    """Check whether a user can perform the given action under their plan.

    Args:
        user_id:    The user performing the action.
        plan_tier:  The user's current billing tier ("free" | "pro" | "team").
        action:     "message" or "ticket".
        db:         Reserved for future DB-backed usage queries.

    Returns:
        LimitResult — always succeeds; never raises.
    """
    try:
        return await _check(user_id, plan_tier, action, db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("check_limits failed non-fatally: %s", exc)
        # Fail open — don't block users due to a metering bug
        plan = get_plan(plan_tier)
        return LimitResult(
            user_id=user_id,
            action=action,
            plan_tier=str(plan_tier),
            current_count=0,
            limit=-1,
        )


async def _check(
    user_id: str,
    plan_tier: str | PlanTier,
    action: Action,
    db,
) -> LimitResult:
    plan = get_plan(plan_tier)

    if action == "message":
        limit = plan.monthly_message_limit
        count = await usage_meter.get_message_count(user_id)
    else:
        limit = plan.monthly_ticket_limit
        count = await usage_meter.get_ticket_count(user_id)

    # Unlimited plan — always allow
    if limit == -1:
        return LimitResult(
            user_id=user_id,
            action=action,
            plan_tier=plan.tier.value,
            current_count=count,
            limit=limit,
        )

    # Hard limit breached
    if count >= limit:
        msg = (
            f"You've reached your {plan.display_name} plan limit of {limit} "
            f"{action}s this month. Upgrade to Pro or Team to continue."
        )
        logger.info("LimitCheck: HARD BLOCK user=%s action=%s count=%d limit=%d", user_id, action, count, limit)
        return LimitResult(
            user_id=user_id,
            action=action,
            plan_tier=plan.tier.value,
            current_count=count,
            limit=limit,
            hard_blocked=True,
            message=msg,
        )

    # Soft limit warning
    soft_threshold = int(limit * plan.soft_limit_pct)
    if count >= soft_threshold:
        remaining = limit - count
        msg = (
            f"Heads up — you've used {count}/{limit} {action}s this month "
            f"({remaining} remaining on the {plan.display_name} plan)."
        )
        logger.debug("LimitCheck: soft warn user=%s action=%s count=%d threshold=%d", user_id, action, count, soft_threshold)
        return LimitResult(
            user_id=user_id,
            action=action,
            plan_tier=plan.tier.value,
            current_count=count,
            limit=limit,
            soft_warning=True,
            message=msg,
        )

    return LimitResult(
        user_id=user_id,
        action=action,
        plan_tier=plan.tier.value,
        current_count=count,
        limit=limit,
    )
