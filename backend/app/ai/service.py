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
    """Structured response from the AI service / agent."""

    response: str
    intent: str
    confidence: float
    should_escalate: bool
    escalation_reason: Optional[str] = None
    # Agent-run metadata (populated by SupportAgent, empty for legacy AIService path)
    tools_called: List[str] = field(default_factory=list)
    iterations: int = 0
    kb_articles_found: int = 0
    ticket_created: bool = False


_LOGIN_KEYWORDS = frozenset({
    "login", "log in", "sign in", "signin", "password", "forgot password",
    "reset password", "account", "credentials", "locked out", "access",
})
_BILLING_KEYWORDS = frozenset({
    "payment", "refund", "billing", "charge", "charged", "invoice",
    "subscription", "billed", "transaction", "receipt", "money", "fee",
})


def _build_fallback_response(user_message: str = "") -> AIResponse:
    """Return a context-aware fallback when the AI service is unreachable.

    Keyword-matches the user message to pick a relevant reply instead of
    the generic "temporary issue" string.  Always sets should_escalate=True
    so a human agent is notified when the AI is unavailable.
    """
    msg = user_message.lower()

    if any(k in msg for k in _LOGIN_KEYWORDS):
        response = (
            "I understand you're facing a login issue. Let me help you troubleshoot this. "
            "Please try resetting your password or checking your credentials. "
            "If the issue continues, I will escalate this to a human support agent immediately."
        )
        intent = "account"
    elif any(k in msg for k in _BILLING_KEYWORDS):
        response = (
            "I see you're having a billing-related issue. Let me assist you with this. "
            "Please check your payment status or recent transactions. "
            "If needed, I can escalate this to our billing team."
        )
        intent = "billing"
    else:
        response = (
            "Thank you for reaching out. I'm here to help you with your request. "
            "Let me analyze your issue and provide the best possible solution. "
            "If needed, I will connect you with a human agent."
        )
        intent = "general"

    return AIResponse(
        response=response,
        intent=intent,
        confidence=0.4,
        should_escalate=True,
        escalation_reason="AI service unavailable — context-aware fallback provided",
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
