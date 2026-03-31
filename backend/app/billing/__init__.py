"""
Phase 6 — SaaS monetization layer.

Provides plan definitions, usage metering, and limit enforcement.
Stripe integration is a future step — this layer handles the business
logic independently of the payment provider.
"""

from app.billing.plans import Plan, PlanTier, get_plan
from app.billing.limits import LimitResult, check_limits
from app.billing.usage_meter import UsageMeter, usage_meter

__all__ = [
    "Plan",
    "PlanTier",
    "get_plan",
    "LimitResult",
    "check_limits",
    "UsageMeter",
    "usage_meter",
]
