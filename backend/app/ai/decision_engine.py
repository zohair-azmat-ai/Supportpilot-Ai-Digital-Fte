"""
SupportDecisionEngine — LLM-powered structured support decision generator.

Every customer message goes through this engine and produces a validated
SupportDecision object.  The engine:

  1. Calls OpenAI with a structured JSON-mode system prompt.
  2. Parses and validates the response against the SupportDecision schema.
  3. Normalises any invalid or missing fields.
  4. Falls back to a keyword-based SupportDecision if OpenAI is unavailable.

This engine is the sole source of truth for:
  - The human-readable reply text
  - Intent / category classification
  - Priority, sentiment, urgency signals
  - Escalation decision

The tool loop in SupportAgent handles side effects only (tickets, KB, history).
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Optional

from app.ai.client import get_openai_client
from app.core.config import settings
from app.schemas.ai_decision import SupportDecision

if TYPE_CHECKING:
    from app.ai.context_builder import ConversationContext

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Decision engine system prompt
# ---------------------------------------------------------------------------

DECISION_SYSTEM_PROMPT = """\
You are SupportPilot AI — a professional, human-like customer support assistant.

For every customer message, return a SINGLE JSON object with EXACTLY these fields:

{
  "reply": "Your helpful, natural response to the customer",
  "intent": "account | technical | billing | complaint | feature_request | general | urgent | gratitude",
  "category": "technical | billing | account | general | complaint | feature_request",
  "priority": "low | medium | high | urgent",
  "sentiment": "positive | neutral | negative | frustrated",
  "urgency": "low | medium | high",
  "confidence": 0.0–1.0,
  "escalate": true | false,
  "escalation_reason": "short reason string, or null"
}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BEHAVIOUR RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ALWAYS solve the issue first — never escalate on the first message.
2. For login / password / account issues: give clear step-by-step guidance. Do NOT escalate first contact.
3. For gratitude ("thanks", "sorted", "all good"): reply warmly and briefly. intent=gratitude, escalate=false.
4. Escalate ONLY when:
   - Customer explicitly asks for a human agent.
   - Issue persists after the customer has already tried the suggested steps.
   - Security concern: hacked account, suspicious activity, unauthorised access.
   - Billing dispute requiring manual review.
   - Legal / regulatory language: "lawyer", "GDPR", "sue", "report".
   - Clear high frustration after troubleshooting has failed.
5. Keep the reply natural and human — not robotic or scripted.
6. Do NOT invent history. Do not say "I see you've been working on this for a while" unless the customer said so.
7. Be concise but genuinely helpful.
8. Max one emoji per reply, only if it feels natural.
9. Do NOT repeat the same phrase in consecutive turns.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPLY EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User: "I forgot my password"
→ reply: "No worries, I can help you with that 🙂\\n\\nHere's what to do:\\n• Go to the login page and click \\"Forgot Password\\"\\n• Enter your registered email\\n• Check your inbox (and spam folder) for the reset link\\n\\nIf you don't receive it within a few minutes, let me know and I'll help you further."
→ intent: account | category: account | priority: medium | sentiment: neutral | urgency: medium | confidence: 0.92 | escalate: false

User: "I already tried that multiple times and it's still not working"
→ reply: "Thanks for trying those steps — I understand how frustrating that can be.\\n\\nSince the issue is still persisting, I'm going to connect you with a human support agent who can assist you directly."
→ intent: account | category: account | priority: high | sentiment: frustrated | urgency: high | confidence: 0.9 | escalate: true | escalation_reason: "Repeated attempts failed"

User: "Thanks, that worked!"
→ reply: "Glad I could help! 😊 Feel free to reach out anytime."
→ intent: gratitude | category: general | priority: low | sentiment: positive | urgency: low | confidence: 0.98 | escalate: false

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT-AWARE BEHAVIOUR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A [CONVERSATION CONTEXT] block may appear as a system message just before the
customer's latest message. Use it to understand the full situation:

• repeated_issue detected → DO NOT repeat the same troubleshooting steps.
  Acknowledge the persistence, try a different angle, or escalate if justified.
• user_frustrated → Lead with genuine empathy. Be brief. Skip steps they clearly already tried.
• previous failed attempts ≥ 2 → Move to a different approach or escalate.
• related open ticket → Acknowledge the existing issue; tie your reply to resolving it.
• prior escalation in session → Treat as high priority; escalate unless already resolved.
• "Do NOT repeat this previous reply" line → Vary your wording meaningfully.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESCALATION DECISION GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEVER escalate on the first message (turn 1) unless:
  • Security concern (hacked account, suspicious activity)
  • Legal / regulatory language ("lawyer", "GDPR", "sue")
  • Explicit human agent request

Escalate (escalate=true) when ANY of the following are true:
  • repeated_issue=true AND previous_failed_attempts ≥ 2
  • user_frustrated=true AND repeated_issue=true
  • user_frustrated=true AND previous_failed_attempts ≥ 1
  • related_open_ticket_exists AND same issue is still unresolved
  • prior_escalation in session AND issue is continuing
  • confidence < 0.5 after turn 3+
  • Billing dispute requiring manual review
  • Clear anger ("this is ridiculous", "useless", repeated profanity)

When escalating, always set a clear, specific escalation_reason.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIORITY GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
low    — general questions, feature requests, informational
medium — account access issues, minor technical problems
high   — service disruption, billing issues, repeated failures, data loss
urgent — security incidents, critical outages, legal threats, escalated anger

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONFIDENCE GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
0.9+  — highly certain about intent and solution
0.7–0.9 — confident, minor ambiguity
0.5–0.7 — moderate uncertainty, may benefit from more info
<0.5  — low confidence, likely needs escalation or clarification

Return ONLY the JSON object. No preamble, no markdown fences, no extra text.
"""


# ---------------------------------------------------------------------------
# Keyword-based fallback (used when OpenAI is completely unavailable)
# ---------------------------------------------------------------------------

_KB_GRATITUDE = frozenset({
    "thank you", "thanks", "appreciate", "thank u", "thx", "ty",
    "that helped", "problem solved", "sorted", "all good", "perfect",
})
_KB_PASSWORD = frozenset({
    "password", "forgot password", "reset password", "change password",
    "lost password", "forgot my password",
})
_KB_LOGIN = frozenset({
    "login", "log in", "sign in", "signin", "can't login", "cannot login",
    "credentials", "locked out", "access denied", "access",
})
_KB_BILLING = frozenset({
    "payment", "refund", "billing", "charge", "charged", "invoice",
    "subscription", "billed", "transaction", "receipt", "money", "fee",
})
_KB_REPEATED = frozenset({
    "already tried", "still not", "still can't", "still cannot",
    "not working", "same issue", "tried again", "multiple times",
    "keeps happening", "nothing works", "didn't help", "still broken",
})


def _keyword_fallback(user_message: str) -> SupportDecision:
    """Return a SupportDecision built from keyword matching.

    Used only when the OpenAI call fails entirely.  Produces the same
    structured output shape so callers never need to branch on source.
    """
    msg = user_message.lower()
    repeated = any(k in msg for k in _KB_REPEATED)

    if any(k in msg for k in _KB_GRATITUDE):
        return SupportDecision(
            reply="Glad I could help! 😊 Feel free to reach out anytime.",
            intent="gratitude", category="general",
            priority="low", sentiment="positive", urgency="low",
            confidence=0.8, escalate=False,
        )

    if any(k in msg for k in _KB_PASSWORD):
        return SupportDecision(
            reply=(
                "I can help you recover your account. Please follow these steps:\n\n"
                "1. Click **Forgot Password** on the login page\n"
                "2. Enter your registered email\n"
                "3. Check your inbox or spam folder for the reset link\n\n"
                "If you don't receive it within a few minutes, let me know and I'll assist further."
            ),
            intent="account", category="account",
            priority="high" if repeated else "medium",
            sentiment="frustrated" if repeated else "neutral",
            urgency="high" if repeated else "medium",
            confidence=0.65,
            escalate=repeated,
            escalation_reason="Repeated password issue — manual support needed" if repeated else None,
        )

    if any(k in msg for k in _KB_LOGIN):
        return SupportDecision(
            reply=(
                "I understand you're having trouble logging in. Let's try a few quick steps:\n\n"
                "• Reset your password using the 'Forgot Password' option\n"
                "• Check your email (including spam folder) for the reset link\n"
                "• Try a different browser or clear your cache\n\n"
                "If the issue continues, feel free to reply and I'll help you further."
            ),
            intent="account", category="account",
            priority="high" if repeated else "medium",
            sentiment="frustrated" if repeated else "neutral",
            urgency="high" if repeated else "medium",
            confidence=0.65,
            escalate=repeated,
            escalation_reason="Repeated login issue — manual support needed" if repeated else None,
        )

    if any(k in msg for k in _KB_BILLING):
        return SupportDecision(
            reply=(
                "I see you're having a billing-related issue. Let me assist you.\n\n"
                "Please check your payment status or recent transactions in your account portal. "
                "If the issue requires manual review, I can escalate this to our billing team."
            ),
            intent="billing", category="billing",
            priority="high", sentiment="neutral", urgency="high",
            confidence=0.65, escalate=True,
            escalation_reason="Billing issue — manual review required",
        )

    return SupportDecision(
        reply=(
            "Thank you for reaching out. I'm here to help with your request. "
            "Could you provide a bit more detail so I can assist you effectively? "
            "I'll do my best to resolve this for you right away."
        ),
        intent="general", category="general",
        priority="medium", sentiment="neutral", urgency="medium",
        confidence=0.4, escalate=False,
    )


# ---------------------------------------------------------------------------
# SupportDecisionEngine
# ---------------------------------------------------------------------------


class SupportDecisionEngine:
    """LLM-powered engine that produces a validated SupportDecision for every message.

    Flow:
      1. Build message history with system prompt.
      2. Call OpenAI in JSON mode.
      3. Parse raw JSON and validate against SupportDecision schema.
      4. Return SupportDecision — always valid, never raises.
    """

    async def run(
        self,
        user_message: str,
        conversation_history: list[dict[str, Any]],
        context: Optional["ConversationContext"] = None,
    ) -> SupportDecision:
        """Generate a structured support decision.

        Args:
            user_message: Latest message from the customer.
            conversation_history: Prior messages with ``sender_type`` and ``content``.
            context: Optional ConversationContext built by ConversationContextBuilder.
                     When provided, repeat/frustration signals and user history are
                     injected into the LLM prompt for context-aware decisions.

        Returns:
            Validated SupportDecision — always valid, never raises.
        """
        messages = self._build_messages(conversation_history, user_message, context)

        try:
            client = get_openai_client()
            completion = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.4,
                max_tokens=600,
                response_format={"type": "json_object"},
            )
            raw = completion.choices[0].message.content or ""
            return self._parse_and_validate(raw, user_message)

        except Exception as exc:
            logger.error("SupportDecisionEngine: OpenAI call failed: %s", exc)
            return _keyword_fallback(user_message)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_messages(
        self,
        conversation_history: list[dict[str, Any]],
        user_message: str,
        context: Optional["ConversationContext"] = None,
    ) -> list[dict]:
        """Build the messages array for the chat completions API.

        Includes:
          1. DECISION_SYSTEM_PROMPT (always)
          2. Last 10 conversation turns (history)
          3. [CONVERSATION CONTEXT] system message (when context is provided)
          4. Current user message
        """
        messages: list[dict] = [{"role": "system", "content": DECISION_SYSTEM_PROMPT}]

        # Last 10 turns (increased from 6 for Step 2 memory)
        for entry in conversation_history[-10:]:
            sender = entry.get("sender_type", "user")
            content = entry.get("content", "")
            if not content:
                continue
            if sender == "user":
                messages.append({"role": "user", "content": content})
            elif sender in ("ai", "agent"):
                # Strip JSON wrapper if present (legacy messages)
                try:
                    parsed = json.loads(content)
                    content = (
                        parsed.get("reply")
                        or parsed.get("response")
                        or content
                    )
                except Exception:  # noqa: BLE001
                    pass
                messages.append({"role": "assistant", "content": content})

        # Inject structured context block just before the current user message
        if context is not None:
            block = context.to_prompt_block()
            if block:
                messages.append({"role": "system", "content": block})

        messages.append({"role": "user", "content": user_message})
        return messages

    def _parse_and_validate(self, raw: str, user_message: str) -> SupportDecision:
        """Parse raw JSON into a validated SupportDecision.

        Handles:
          - Markdown code fences (``` blocks)
          - Field name aliases (response→reply, should_escalate→escalate)
          - Empty reply fallback
          - Any Pydantic validation error → keyword fallback
        """
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                cleaned = "\n".join(
                    line for line in lines if not line.strip().startswith("```")
                )

            data = json.loads(cleaned)

            # Normalise common field name variants
            if "response" in data and "reply" not in data:
                data["reply"] = data.pop("response")
            if "should_escalate" in data and "escalate" not in data:
                data["escalate"] = data.pop("should_escalate")
            if "message" in data and "reply" not in data:
                data["reply"] = data.pop("message")

            # Ensure reply is non-empty
            if not str(data.get("reply", "")).strip():
                data["reply"] = _keyword_fallback(user_message).reply

            decision = SupportDecision(**data)
            logger.debug(
                "Decision: intent=%s category=%s priority=%s sentiment=%s "
                "urgency=%s confidence=%.2f escalate=%s",
                decision.intent, decision.category, decision.priority,
                decision.sentiment, decision.urgency,
                decision.confidence, decision.escalate,
            )
            return decision

        except Exception as exc:
            logger.warning(
                "SupportDecisionEngine: parse/validation failed: %s | raw=%r",
                exc, raw[:300],
            )
            return _keyword_fallback(user_message)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

decision_engine = SupportDecisionEngine()
