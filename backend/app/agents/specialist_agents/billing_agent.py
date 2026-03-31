"""
BillingAgent — specialist for payment, subscription, and invoice queries.

Handles intents: payment_failed · subscription · refund · invoice

Phase 6 — interface defined, LLM specialisation to be wired in
when the multi-agent pipeline is activated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Billing-specific system prompt prefix injected before the shared context block.
_BILLING_SYSTEM_PREFIX = """\
You are SupportPilot Billing Specialist — an expert on payment processing,
subscription plans, invoices, and refunds.

Focus areas:
  • Payment failures — explain decline reasons and retry steps clearly
  • Subscription changes — upgrades, downgrades, cancellation policies
  • Refund requests — eligibility, timelines, and escalation path
  • Invoice queries — breakdown, VAT, and download instructions

Keep replies concise (≤ 100 words), empathetic, and action-oriented.
Never speculate on account-specific billing data you don't have.
"""


@dataclass
class SpecialistRequest:
    """Minimal request type shared across all specialist agents."""
    message: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    context_block: str = ""          # injected prompt block from ConversationContextBuilder
    metadata: dict = field(default_factory=dict)


@dataclass
class SpecialistResponse:
    """Response from any specialist agent."""
    reply: str
    specialist: str
    escalate: bool = False
    confidence: float = 0.9
    metadata: dict = field(default_factory=dict)


class BillingAgent:
    """Specialist agent for billing and payment queries."""

    SPECIALIST_NAME = "billing"

    async def handle(
        self,
        request: SpecialistRequest,
        db: Any = None,
    ) -> SpecialistResponse:
        """Process a billing-related support request.

        Phase 6 stub — returns a structured placeholder until the full
        LLM specialisation is wired into the pipeline.

        Args:
            request: SpecialistRequest with message and context.
            db:      AsyncSession (reserved for future KB/DB lookups).

        Returns:
            SpecialistResponse with reply and metadata.
        """
        logger.info(
            "BillingAgent.handle: conversation=%s user=%s",
            request.conversation_id,
            request.user_id,
        )

        # Phase 6 stub — real LLM call to be added when pipeline is activated
        reply = self._keyword_response(request.message)

        return SpecialistResponse(
            reply=reply,
            specialist=self.SPECIALIST_NAME,
            escalate=False,
            confidence=0.85,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _keyword_response(self, message: str) -> str:
        """Lightweight keyword-based fallback for the stub phase."""
        msg = message.lower()
        if any(k in msg for k in ("payment", "charge", "fail", "declined")):
            return (
                "I can see you're having a payment issue. "
                "Common causes include expired cards, insufficient funds, or a bank block. "
                "Could you confirm the last 4 digits of the card used so I can check further?"
            )
        if any(k in msg for k in ("refund", "money back", "reimburse")):
            return (
                "Refund requests are typically processed within 5–7 business days. "
                "To raise one, I'll need your order or invoice number — "
                "could you share that?"
            )
        if any(k in msg for k in ("cancel", "subscription", "plan", "upgrade", "downgrade")):
            return (
                "I can help with your subscription. "
                "Are you looking to upgrade, downgrade, or cancel? "
                "Let me know and I'll walk you through the steps."
            )
        return (
            "I'm the billing specialist here to help with payments, invoices, "
            "and subscriptions. Could you describe what you're seeing?"
        )


# Module-level singleton
billing_agent = BillingAgent()
