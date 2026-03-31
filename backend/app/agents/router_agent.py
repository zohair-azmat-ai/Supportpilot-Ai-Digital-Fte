"""
RouterAgent — Phase 6 multi-agent dispatcher.

Inspects the `category` and `intent` from the AI decision and routes
to the correct specialist agent.  Falls back to None (caller uses the
default SupportAgent) when no specialist matches.

Usage (Phase 6 — not yet wired into the main pipeline):

    from app.agents.router_agent import router_agent

    specialist = router_agent.resolve(category="billing", intent="payment_failed")
    if specialist:
        result = await specialist.handle(request, context)
    else:
        result = await default_agent.run(...)
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Map of category → specialist agent module name.
# Populated lazily to avoid circular imports at startup.
_CATEGORY_MAP: dict[str, str] = {
    "billing":   "billing",
    "technical": "technical",
    "account":   "account",
}

# Intent-level overrides (take priority over category match)
_INTENT_MAP: dict[str, str] = {
    "payment_failed":    "billing",
    "subscription":      "billing",
    "refund":            "billing",
    "password_reset":    "account",
    "login_issue":       "account",
    "account_locked":    "account",
    "2fa":               "account",
    "app_crash":         "technical",
    "slow_performance":  "technical",
    "data_missing":      "technical",
    "feature_missing":   "technical",
}


class RouterAgent:
    """Resolves the correct specialist agent for a given category/intent pair."""

    def resolve(
        self,
        category: Optional[str] = None,
        intent: Optional[str] = None,
    ):
        """Return a specialist agent instance, or None if no specialist applies.

        Args:
            category: AI-detected category ("billing" | "technical" | "account" | "general")
            intent:   AI-detected intent slug (e.g. "payment_failed", "app_crash")

        Returns:
            A specialist agent instance with a `.handle()` method, or None.
        """
        specialist_name = self._pick_specialist(category, intent)
        if not specialist_name:
            return None
        return self._load_specialist(specialist_name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _pick_specialist(
        self,
        category: Optional[str],
        intent: Optional[str],
    ) -> Optional[str]:
        """Return the specialist name string, or None."""
        # Intent overrides take highest priority
        if intent:
            for key, name in _INTENT_MAP.items():
                if key in intent.lower():
                    logger.debug("RouterAgent: intent '%s' → %s specialist", intent, name)
                    return name

        # Fall back to category match
        if category:
            name = _CATEGORY_MAP.get(category.lower())
            if name:
                logger.debug("RouterAgent: category '%s' → %s specialist", category, name)
                return name

        return None

    def _load_specialist(self, name: str):
        """Lazily import and return the specialist agent singleton."""
        try:
            if name == "billing":
                from app.agents.specialist_agents.billing_agent import billing_agent
                return billing_agent
            if name == "technical":
                from app.agents.specialist_agents.technical_agent import technical_agent
                return technical_agent
            if name == "account":
                from app.agents.specialist_agents.account_agent import account_agent
                return account_agent
        except ImportError as exc:
            logger.warning("RouterAgent: could not load %s specialist: %s", name, exc)
        return None


# Module-level singleton
router_agent = RouterAgent()
