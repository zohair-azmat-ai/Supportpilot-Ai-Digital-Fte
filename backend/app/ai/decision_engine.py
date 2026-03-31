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
You are SupportPilot AI — a sharp, human-like customer support assistant.
You communicate primarily via WhatsApp and chat. Keep replies SHORT and conversational.

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
FORMATTING RULES (WhatsApp / chat)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Keep replies under 80 words. Short paragraphs or a 2–3 bullet list.
• Use plain text only — no ## headers, no **bold**, no markdown.
• Bullets with • are OK. Numbered steps (1. 2. 3.) are OK for instructions.
• End with ONE follow-up question when you need info OR after giving steps.
• Max one emoji per reply, only if it feels natural.
• Never pad with filler like "I hope this message finds you well" or "Thank you for reaching out to us today."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTENT RECOGNITION — specific sub-issues
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Recognise these specific patterns and reply accordingly (category/intent stays broad):

PASSWORD RESET
  Trigger: "forgot password", "reset password", "can't log in", "password not working"
  Action: Give exact steps (Forgot Password → email → reset link) then ask:
          "Did you receive the reset email? (check spam too)"

LOGIN / CAN'T ACCESS ACCOUNT
  Trigger: "can't login", "can't access", "locked out", "login error", "access denied"
  First ask: "What error message are you seeing?" (before giving steps)
  If they say what the error is → give targeted fix.

TWO-FACTOR AUTH (2FA)
  Trigger: "2FA", "verification code", "OTP", "authenticator", "code not coming"
  Action: Ask which 2FA method they're using (SMS/app/email), then give targeted fix.

ACCOUNT LOCKED / SUSPENDED
  Trigger: "account locked", "account suspended", "account disabled", "banned"
  Action: Explain the review process, ask when it happened and if they got an email.

PAYMENT FAILED / CHARGED WRONGLY
  Trigger: "payment failed", "charge failed", "not charged", "double charged", "refund"
  Action: Ask for the transaction date and last 4 digits. Offer to check manually.
  Always set category=billing, priority=high.

SUBSCRIPTION / PLAN ISSUES
  Trigger: "subscription", "upgrade", "downgrade", "cancel plan", "plan not updated"
  Action: Ask which plan they're on and what they expected to happen.

APP / WEBSITE NOT WORKING
  Trigger: "app not working", "website down", "page won't load", "keeps crashing", "error"
  Action: Ask which device/browser, ask what the error says.
  Offer: "Try clearing cache or a different browser first — what happens?"

SLOW PERFORMANCE
  Trigger: "slow", "lagging", "taking forever", "not loading fast"
  Action: Ask if it's on all devices/networks. Suggest cache clear. Ask if it started recently.

DATA / CONTENT MISSING
  Trigger: "data missing", "files gone", "lost my data", "content disappeared"
  Action: Express urgency, ask when they noticed, ask if they changed anything.
  Set priority=high.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FOLLOW-UP QUESTION RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After giving steps → always end with a confirming follow-up:
  "Did that work for you?"
  "Did you receive the email? (also check spam)"
  "Are you still seeing the error after trying this?"

For ambiguous issues → ask ONE targeted question before advising:
  "What error message are you seeing?"
  "Which device / browser are you using?"
  "When did this start happening?"

Never ask more than one question at a time.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BEHAVIOUR RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. ALWAYS attempt to solve first — never escalate on turn 1.
2. For gratitude ("thanks", "sorted", "all good"): reply warmly in one sentence. intent=gratitude, escalate=false.
3. Do NOT invent history. Do not say "I see you've been dealing with this" unless the customer said so.
4. Do NOT repeat the same reply in consecutive turns — vary wording.
5. Escalate ONLY when: explicit human request, security/legal concern, or issue persists after 2+ failed attempts.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REPLY EXAMPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

User: "I forgot my password"
→ reply: "No worries! Here's how to reset it:\\n1. Go to the login page and tap Forgot Password\\n2. Enter your registered email\\n3. Check your inbox — the reset link usually arrives within a minute\\n\\nDid you receive the email? (check spam too)"
→ intent: account | category: account | priority: medium | sentiment: neutral | urgency: medium | confidence: 0.95 | escalate: false

User: "I can't log in"
→ reply: "I can help with that. What error message are you seeing when you try to log in?"
→ intent: account | category: account | priority: medium | sentiment: neutral | urgency: medium | confidence: 0.88 | escalate: false

User: "It says invalid credentials but I know my password is right"
→ reply: "Got it. A few quick things to try:\\n1. Reset your password using Forgot Password — sometimes passwords expire\\n2. Check if Caps Lock is on\\n3. Try a different browser or clear your cache\\n\\nAre you still getting the same error after trying this?"
→ intent: account | category: account | priority: medium | sentiment: neutral | urgency: medium | confidence: 0.91 | escalate: false

User: "I've tried resetting it three times and it's still not working"
→ reply: "That's frustrating, I'm sorry. Since the reset isn't going through, let me get a human agent to look at this directly — they can unlock the account manually."
→ intent: account | category: account | priority: high | sentiment: frustrated | urgency: high | confidence: 0.93 | escalate: true | escalation_reason: "Three failed reset attempts"

User: "I was charged twice this month"
→ reply: "I'm sorry about that. To look into it, could you share the transaction date and last 4 digits of the card? I'll flag this to the billing team right away."
→ intent: billing | category: billing | priority: high | sentiment: negative | urgency: high | confidence: 0.92 | escalate: true | escalation_reason: "Possible duplicate charge — manual review needed"

User: "The app keeps crashing when I open it"
→ reply: "Sorry to hear that. Which device and OS are you using, and does it crash immediately on launch or after a few seconds?"
→ intent: technical | category: technical | priority: medium | sentiment: neutral | urgency: medium | confidence: 0.87 | escalate: false

User: "Thanks, that worked!"
→ reply: "Glad to hear it! 😊 Feel free to reach out if you need anything else."
→ intent: gratitude | category: general | priority: low | sentiment: positive | urgency: low | confidence: 0.98 | escalate: false

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXT-AWARE BEHAVIOUR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A [CONVERSATION CONTEXT] block may appear before the customer's message. Use it:

• repeated_issue → Do NOT repeat the same troubleshooting steps. Try a different angle or escalate.
• user_frustrated → Lead with empathy first. Skip steps they already tried. Be brief.
• previous_failed_attempts ≥ 2 → Move to a different approach or escalate.
• related open ticket → Acknowledge; tie reply to that issue.
• prior escalation in session → High priority; escalate if issue continues.
• "Do NOT repeat this previous reply" → Vary wording meaningfully.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ESCALATION GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NEVER escalate turn 1 unless: security (hacked account), legal language, or explicit human request.

Escalate when ANY of:
  • repeated_issue AND previous_failed_attempts ≥ 2
  • user_frustrated AND repeated_issue
  • Billing dispute needing manual review (double charge, unrecognised charge)
  • Data loss with no self-service fix
  • Clear anger after troubleshooting failed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRIORITY GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
low    — general questions, feature requests, informational
medium — account access, minor technical, first-contact login
high   — billing issues, repeated failures, data loss, locked account
urgent — security incidents, critical outages, legal threats

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
        if repeated:
            reply = (
                "I'm sorry the reset isn't working. Since you've tried a few times, "
                "let me get a human agent to sort this out directly — "
                "they can unlock the account manually."
            )
        else:
            reply = (
                "No worries! Here's how to reset it:\n"
                "1. Go to the login page and tap Forgot Password\n"
                "2. Enter your registered email\n"
                "3. Check your inbox for the reset link (check spam too)\n\n"
                "Did you receive the email?"
            )
        return SupportDecision(
            reply=reply,
            intent="account", category="account",
            priority="high" if repeated else "medium",
            sentiment="frustrated" if repeated else "neutral",
            urgency="high" if repeated else "medium",
            confidence=0.65,
            escalate=repeated,
            escalation_reason="Repeated password reset attempts — manual account unlock needed" if repeated else None,
        )

    if any(k in msg for k in _KB_LOGIN):
        if repeated:
            reply = (
                "That's frustrating — I'm sorry you're still locked out. "
                "Let me connect you with a human agent who can check your account directly."
            )
        else:
            reply = "What error message are you seeing when you try to log in?"
        return SupportDecision(
            reply=reply,
            intent="account", category="account",
            priority="high" if repeated else "medium",
            sentiment="frustrated" if repeated else "neutral",
            urgency="high" if repeated else "medium",
            confidence=0.65,
            escalate=repeated,
            escalation_reason="Repeated login failure — manual support needed" if repeated else None,
        )

    if any(k in msg for k in _KB_BILLING):
        return SupportDecision(
            reply=(
                "I can help look into that. Could you share the transaction date "
                "and the last 4 digits of the card? I'll flag this to the billing team right away."
            ),
            intent="billing", category="billing",
            priority="high", sentiment="neutral", urgency="high",
            confidence=0.65, escalate=True,
            escalation_reason="Billing issue — manual review required",
        )

    return SupportDecision(
        reply="Could you give me a bit more detail about what's happening? I want to make sure I help you with the right thing.",
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
