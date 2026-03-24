"""AI service: generates structured responses using OpenAI."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from openai import APIError, APITimeoutError

from app.ai.client import get_openai_client
from app.ai.prompts import SUPPORT_SYSTEM_PROMPT
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class AIResponse:
    """Structured response from the AI service / agent.

    Core fields (always populated):
        response          — Human-readable reply text
        intent            — Intent category (account, billing, technical, …)
        confidence        — LLM confidence 0.0–1.0
        should_escalate   — Whether to escalate to a human agent
        escalation_reason — Reason string if escalation is flagged

    Structured decision fields (populated by SupportDecisionEngine):
        category  — Support category for ticket routing
        priority  — Ticket priority level (low/medium/high/urgent)
        sentiment — Customer sentiment (positive/neutral/negative/frustrated)
        urgency   — Issue urgency (low/medium/high)

    Agent-run metadata (populated by the tool loop):
        tools_called      — List of tool names invoked
        iterations        — Number of agent loop iterations
        kb_articles_found — KB articles retrieved
        ticket_created    — Whether a ticket was created
    """

    response: str
    intent: str
    confidence: float
    should_escalate: bool
    escalation_reason: Optional[str] = None
    # Structured decision fields — from SupportDecisionEngine
    category: str = "general"
    priority: str = "medium"
    sentiment: str = "neutral"
    urgency: str = "medium"
    # Agent-run metadata
    tools_called: List[str] = field(default_factory=list)
    iterations: int = 0
    kb_articles_found: int = 0
    ticket_created: bool = False


_GRATITUDE_KEYWORDS = frozenset({
    "thank you", "thanks", "appreciate", "thank u", "thx", "ty",
    "that helped", "helpful", "problem solved", "sorted", "all good",
})
_REPEATED_LOGIN_KEYWORDS = frozenset({
    "multiple attempts", "tried multiple", "tried again", "keep trying",
    "still can't", "still cannot", "account locked", "locked", "blocked",
    "already tried", "tried everything", "attempts",
})
_PASSWORD_KEYWORDS = frozenset({
    "password", "forgot password", "reset password", "change password",
    "lost password", "forgot my password",
})
_LOGIN_KEYWORDS = frozenset({
    "login", "log in", "sign in", "signin", "can't login", "cannot login",
    "credentials", "locked out", "access denied", "access",
})
_BILLING_KEYWORDS = frozenset({
    "payment", "refund", "billing", "charge", "charged", "invoice",
    "subscription", "billed", "transaction", "receipt", "money", "fee",
})


def _build_fallback_response(user_message: str = "") -> AIResponse:
    """Return a context-aware fallback when the AI service is unreachable.

    Priority order: gratitude → repeated login → password → login → billing → general.
    Simple first-contact issues (login, password) do NOT auto-escalate — troubleshoot first.
    Escalation is reserved for repeated failures, locked accounts, billing, and security.
    """
    msg = user_message.lower()

    # 1. Gratitude — close the conversation politely, no escalation needed
    if any(k in msg for k in _GRATITUDE_KEYWORDS):
        return AIResponse(
            response=(
                "Glad I could help! 😊\n"
                "If you need anything else, feel free to reach out anytime."
            ),
            intent="gratitude",
            confidence=0.8,
            should_escalate=False,
        )

    # 2. Repeated login attempts — account locked / multiple failures
    if (
        any(k in msg for k in _REPEATED_LOGIN_KEYWORDS)
        and any(k in msg for k in _LOGIN_KEYWORDS | _PASSWORD_KEYWORDS)
    ):
        return AIResponse(
            response=(
                "It looks like there may have been multiple login attempts. "
                "Please try the following:\n\n"
                "• Wait 15–30 minutes before retrying\n"
                "• Disable any VPN or proxy\n"
                "• Ensure your device time is synced\n\n"
                "Still not working? I'll escalate this to our account team right away."
            ),
            intent="account",
            confidence=0.5,
            should_escalate=True,
            escalation_reason="Multiple login attempts detected — account may be locked",
        )

    # 3. Password reset / recovery — troubleshoot first, no escalation on first contact
    if any(k in msg for k in _PASSWORD_KEYWORDS):
        return AIResponse(
            response=(
                "I can help you recover your account. Please follow these steps:\n\n"
                "1. Click **Forgot Password** on the login page\n"
                "2. Enter your registered email\n"
                "3. Check your inbox or spam folder for the reset link\n\n"
                "If you don't receive it within a few minutes, "
                "let me know and I'll assist further."
            ),
            intent="account",
            confidence=0.6,
            should_escalate=False,
        )

    # 4. General login / sign-in issue — troubleshoot first, no escalation on first contact
    if any(k in msg for k in _LOGIN_KEYWORDS):
        return AIResponse(
            response=(
                "I understand you're having trouble logging in. "
                "Let's try a few quick steps:\n\n"
                "• Reset your password using the 'Forgot Password' option\n"
                "• Check your email (including spam folder) for the reset link\n"
                "• Try a different browser or clear your cache\n\n"
                "If the issue continues, feel free to reply and I'll help you further."
            ),
            intent="account",
            confidence=0.6,
            should_escalate=False,
        )

    # 5. Billing issue
    if any(k in msg for k in _BILLING_KEYWORDS):
        return AIResponse(
            response=(
                "I see you're having a billing-related issue. Let me assist you with this. "
                "Please check your payment status or recent transactions. "
                "If needed, I can escalate this to our billing team."
            ),
            intent="billing",
            confidence=0.5,
            should_escalate=True,
            escalation_reason="AI service unavailable — billing fallback provided",
        )

    # 6. General fallback
    return AIResponse(
        response=(
            "Thank you for reaching out. I'm here to help you with your request. "
            "Let me look into this and provide the best possible solution. "
            "If needed, I will connect you with a human agent right away."
        ),
        intent="general",
        confidence=0.4,
        should_escalate=True,
        escalation_reason="AI service unavailable — general fallback provided",
    )


class AIService:
    """Handles communication with the OpenAI API and parses structured output."""

    def _build_messages(
        self,
        conversation_history: List[Dict[str, Any]],
        user_message: str,
    ) -> List[Dict[str, str]]:
        """Build the messages array for the chat completion request."""
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": SUPPORT_SYSTEM_PROMPT}
        ]

        for entry in conversation_history:
            sender = entry.get("sender_type", "user")
            content = entry.get("content", "")
            if sender == "user":
                messages.append({"role": "user", "content": content})
            elif sender in ("ai", "agent"):
                # Convert AI/agent messages to assistant role
                # Strip JSON wrapper if present so history is readable
                try:
                    parsed = json.loads(content)
                    assistant_text = parsed.get("response", content)
                except (json.JSONDecodeError, TypeError):
                    assistant_text = content
                messages.append({"role": "assistant", "content": assistant_text})

        messages.append({"role": "user", "content": user_message})
        return messages

    def _parse_response(self, raw: str) -> AIResponse:
        """Parse JSON from the model response into an AIResponse.

        Falls back gracefully if the JSON is malformed.
        """
        try:
            # The model may wrap the JSON in markdown code fences
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                # Strip opening and closing fences
                cleaned = "\n".join(
                    line
                    for line in lines
                    if not line.strip().startswith("```")
                )

            data = json.loads(cleaned)
            return AIResponse(
                response=str(data.get("response", "")),
                intent=str(data.get("intent", "general")),
                confidence=float(data.get("confidence", 0.5)),
                should_escalate=bool(data.get("should_escalate", False)),
                escalation_reason=data.get("escalation_reason") or None,
            )
        except (json.JSONDecodeError, ValueError, KeyError) as exc:
            logger.warning("Failed to parse AI JSON response: %s | raw=%r", exc, raw)
            # Return a basic response using the raw text
            return AIResponse(
                response=raw or _build_fallback_response().response,
                intent="general",
                confidence=0.5,
                should_escalate=False,
                escalation_reason=None,
            )

    async def generate_response(
        self,
        conversation_history: List[Dict[str, Any]],
        user_message: str,
    ) -> AIResponse:
        """Generate an AI response for a customer message.

        Args:
            conversation_history: List of previous message dicts with
                ``sender_type`` and ``content`` keys.
            user_message: The latest message from the customer.

        Returns:
            Structured ``AIResponse`` instance.
        """
        client = get_openai_client()
        messages = self._build_messages(conversation_history, user_message)

        try:
            completion = await client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,  # type: ignore[arg-type]
                temperature=0.4,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
            raw_content = completion.choices[0].message.content or ""
            return self._parse_response(raw_content)

        except (APIError, APITimeoutError) as exc:
            logger.error("OpenAI API error: %s", exc)
            return _build_fallback_response(user_message)
        except Exception as exc:  # noqa: BLE001
            logger.error("Unexpected error calling OpenAI: %s", exc)
            return _build_fallback_response(user_message)


# Module-level singleton
ai_service = AIService()
