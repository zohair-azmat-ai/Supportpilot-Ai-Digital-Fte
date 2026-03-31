"""
EscalationEngine — deterministic post-processing layer on top of LLM escalation.

Architecture:

  LLM SupportDecisionEngine  →  SupportDecision (escalate, escalation_reason)
                                       ↓
  EscalationEngine.evaluate()  →  EscalationDecision (escalate, reason, level, cause)
                                       ↓
  SupportAgent merges both   →  final AIResponse

Responsibilities:
  1. Hard-rule overrides — security, legal, explicit human-request keywords always
     force escalation regardless of the LLM's decision.
  2. Context-signal rules — frustration, repeated failures, low confidence, and open
     tickets trigger soft escalation when the LLM might have been too conservative.
  3. Anti-over-escalation — simple first-contact issues are explicitly blocked from
     escalation even if the LLM chose to escalate.
  4. Cause labelling — assigns a structured escalation_cause for analytics tracking.
  5. Reply amendment — when the engine upgrades a non-escalation to escalation, it
     appends a short natural-language note to the LLM reply so the customer is informed.

Escalation levels:
  none   — no escalation
  soft   — escalated, but not urgent; queue for human review
  urgent — immediate human intervention required (security, legal, explicit request)

Escalation causes (for analytics):
  security | legal | explicit_human_request | frustration | repeated_issue |
  low_confidence | open_ticket_repeat | llm_decision
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from app.ai.context_builder import ConversationContext
    from app.schemas.ai_decision import SupportDecision

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Keyword sets for hard-rule detection
# ---------------------------------------------------------------------------

_SECURITY_KEYWORDS = frozenset({
    "hacked", "hack", "hacking", "compromised", "unauthorized", "unauthorised",
    "suspicious activity", "suspicious login", "someone else logged",
    "not me", "wasn't me", "wasn't me", "stolen account", "account stolen",
    "account taken over", "data breach", "my data", "phishing", "scam", "fraud",
    "account was accessed", "account compromised",
})

_EXPLICIT_HUMAN_KEYWORDS = frozenset({
    "human agent", "human support", "real person", "speak to someone",
    "talk to a person", "connect me to", "talk to someone",
    "speak to a human", "i want a human", "want to talk to", "need a human",
    "live agent", "live support", "customer service representative",
    "human representative", "talk to an agent", "speak with an agent",
    "want to speak", "let me speak", "get me a human",
})

# Multi-word phrases matched as substrings — safe because they don't appear
# inside common words.
_LEGAL_PHRASES = frozenset({
    "lawyer", "attorney", "legal action", "lawsuit", "suing",
    "gdpr", "data protection regulation", "going to report",
    "regulatory", "regulator", "ombudsman", "legal team", "file a complaint",
    "small claims",
})
# Single words that need word-boundary matching to avoid false positives
# e.g. "sue" inside "issue", "scam" ambiguous in some contexts.
_LEGAL_WORD_BOUNDARY = re.compile(r"\bsue\b|\bsued\b")


def _has_legal_language(msg: str) -> bool:
    """Return True if the message contains legal/regulatory language."""
    return (
        any(phrase in msg for phrase in _LEGAL_PHRASES)
        or bool(_LEGAL_WORD_BOUNDARY.search(msg))
    )

# Simple categories that should not escalate on first contact
_SAFE_FIRST_CONTACT_CATEGORIES = frozenset({
    "account", "general", "feature_request",
})


# ---------------------------------------------------------------------------
# EscalationDecision
# ---------------------------------------------------------------------------


@dataclass
class EscalationDecision:
    """Result of the EscalationEngine evaluation."""

    escalate: bool
    escalation_reason: Optional[str]
    escalation_level: str        # "none" | "soft" | "urgent"
    escalation_cause: Optional[str]  # structured label for analytics


# ---------------------------------------------------------------------------
# EscalationEngine
# ---------------------------------------------------------------------------


class EscalationEngine:
    """Deterministic rule engine that supplements the LLM escalation decision.

    Safe by design — any unhandled exception falls back to honouring the LLM's
    decision without crashing the request pipeline.
    """

    # Short natural-language escalation notes keyed by cause
    _ESCALATION_NOTES: dict[str, str] = {
        "security": (
            "I've flagged your account for immediate review by our security team — "
            "they'll be in touch with you very shortly."
        ),
        "legal": (
            "I'm escalating this to our specialist team so it can be handled "
            "with the attention it deserves."
        ),
        "explicit_human_request": (
            "I'm connecting you with a human support agent right now — "
            "they'll be able to assist you directly."
        ),
        "frustration": (
            "I can see this hasn't been resolved to your satisfaction. "
            "I'm escalating this to a human agent who can look into it further."
        ),
        "repeated_issue": (
            "Since this issue is persisting, I'm escalating it to a human support agent "
            "so they can investigate and resolve it for you."
        ),
        "low_confidence": (
            "To make sure your issue gets the right attention, "
            "I'm passing this to a human support agent now."
        ),
        "open_ticket_repeat": (
            "I can see you have an open ticket for a similar issue. "
            "I'm escalating this so a human agent can review and resolve it end-to-end."
        ),
    }

    def evaluate(
        self,
        context: Optional["ConversationContext"],
        llm_decision: "SupportDecision",
        user_message: str,
    ) -> EscalationDecision:
        """Evaluate and return a final EscalationDecision.

        Args:
            context:      ConversationContext built before the LLM call (may be None).
            llm_decision: SupportDecision produced by the LLM decision engine.
            user_message: Raw customer message text.

        Returns:
            EscalationDecision — always valid, never raises.
        """
        try:
            return self._evaluate(context, llm_decision, user_message)
        except Exception as exc:  # noqa: BLE001
            logger.warning("EscalationEngine.evaluate failed (safe fallback): %s", exc)
            return EscalationDecision(
                escalate=llm_decision.escalate,
                escalation_reason=llm_decision.escalation_reason,
                escalation_level="urgent" if llm_decision.escalate else "none",
                escalation_cause="llm_decision" if llm_decision.escalate else None,
            )

    def build_escalation_note(
        self,
        esc: EscalationDecision,
        context: Optional["ConversationContext"] = None,
    ) -> str:
        """Return a short, natural escalation sentence for appending to the reply.

        For the 'open_ticket_repeat' cause, the "I can see you have an open ticket"
        phrasing is only used when the context confirms a real open ticket exists.
        If the context says otherwise (or is unavailable), a generic message is
        used instead so the AI never falsely claims an open ticket exists.
        """
        _GENERIC = "I'm escalating this to our support team so they can assist you further."

        if esc.escalation_cause == "open_ticket_repeat":
            has_real_open_ticket = (
                context is not None and getattr(context, "related_open_ticket_exists", False)
            )
            if has_real_open_ticket:
                return self._ESCALATION_NOTES["open_ticket_repeat"]
            return _GENERIC

        return self._ESCALATION_NOTES.get(esc.escalation_cause or "", _GENERIC)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _evaluate(
        self,
        context: Optional["ConversationContext"],
        llm_decision: "SupportDecision",
        user_message: str,
    ) -> EscalationDecision:
        msg = user_message.lower()

        # ------------------------------------------------------------------
        # 1. Hard rules — always override LLM (even on first contact)
        # ------------------------------------------------------------------

        if any(kw in msg for kw in _SECURITY_KEYWORDS):
            logger.info("EscalationEngine: security keyword detected")
            return EscalationDecision(
                escalate=True,
                escalation_reason="Security concern detected — account may be compromised.",
                escalation_level="urgent",
                escalation_cause="security",
            )

        if any(kw in msg for kw in _EXPLICIT_HUMAN_KEYWORDS):
            logger.info("EscalationEngine: explicit human request detected")
            return EscalationDecision(
                escalate=True,
                escalation_reason="Customer explicitly requested a human agent.",
                escalation_level="urgent",
                escalation_cause="explicit_human_request",
            )

        if _has_legal_language(msg):
            logger.info("EscalationEngine: legal keyword detected")
            return EscalationDecision(
                escalate=True,
                escalation_reason="Legal or regulatory language detected.",
                escalation_level="urgent",
                escalation_cause="legal",
            )

        # ------------------------------------------------------------------
        # 2. First-contact hard block — no escalation on turn 1 unless a
        #    hard rule already triggered above (security/legal/human request).
        #    This applies regardless of the LLM decision so cross-session
        #    context (open tickets, similar issues) never escalates a fresh
        #    message.
        # ------------------------------------------------------------------
        is_first_contact = context.is_first_contact if context else True
        if is_first_contact:
            logger.info(
                "EscalationEngine: first contact — suppressing escalation "
                "(llm_decision.escalate=%s)",
                llm_decision.escalate,
            )
            return EscalationDecision(
                escalate=False,
                escalation_reason=None,
                escalation_level="none",
                escalation_cause=None,
            )

        # ------------------------------------------------------------------
        # 3. Context-signal rules (require context object)
        # ------------------------------------------------------------------
        if context is not None:

            # Frustration signal with at least one prior failed attempt → soft escalation.
            # Frustration alone (turn 2 with no prior attempts) is not enough —
            # the AI should first try a targeted question before escalating.
            if context.user_frustrated and context.previous_failed_attempts >= 1:
                reason = (
                    llm_decision.escalation_reason
                    or "User is frustrated after repeated failed attempts."
                )
                logger.info(
                    "EscalationEngine: frustration + attempts=%d triggered",
                    context.previous_failed_attempts,
                )
                return EscalationDecision(
                    escalate=True,
                    escalation_reason=reason,
                    escalation_level="soft",
                    escalation_cause="frustration",
                )

            # Repeated issue + two or more failed attempts → soft escalation.
            # Threshold is 2 (not 1) so the AI gets one diagnostic turn before
            # escalating — matching the three-case response strategy.
            if context.repeated_issue and context.previous_failed_attempts >= 2:
                reason = (
                    llm_decision.escalation_reason
                    or (
                        f"Issue is recurring with "
                        f"{context.previous_failed_attempts} failed attempt(s)."
                    )
                )
                logger.info(
                    "EscalationEngine: repeated_issue cause=%s attempts=%d",
                    reason, context.previous_failed_attempts,
                )
                return EscalationDecision(
                    escalate=True,
                    escalation_reason=reason,
                    escalation_level="soft",
                    escalation_cause="repeated_issue",
                )

            # Low LLM confidence after repeated attempts → soft escalation
            if llm_decision.confidence < 0.55 and context.previous_failed_attempts > 0:
                logger.info(
                    "EscalationEngine: low_confidence cause confidence=%.2f attempts=%d",
                    llm_decision.confidence, context.previous_failed_attempts,
                )
                return EscalationDecision(
                    escalate=True,
                    escalation_reason="Low confidence in resolution after repeated attempts.",
                    escalation_level="soft",
                    escalation_cause="low_confidence",
                )

            # Related open ticket still unresolved (not first contact) → soft escalation
            if context.related_open_ticket_exists and not context.is_first_contact:
                reason = (
                    llm_decision.escalation_reason
                    or "An open ticket already exists for this issue."
                )
                logger.info("EscalationEngine: open_ticket_repeat triggered")
                return EscalationDecision(
                    escalate=True,
                    escalation_reason=reason,
                    escalation_level="soft",
                    escalation_cause="open_ticket_repeat",
                )

        # ------------------------------------------------------------------
        # 4. Fall-through: honour LLM decision and label the cause
        # ------------------------------------------------------------------
        if llm_decision.escalate:
            return EscalationDecision(
                escalate=True,
                escalation_reason=llm_decision.escalation_reason,
                escalation_level="soft",
                escalation_cause="llm_decision",
            )

        return EscalationDecision(
            escalate=False,
            escalation_reason=None,
            escalation_level="none",
            escalation_cause=None,
        )


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

escalation_engine = EscalationEngine()
