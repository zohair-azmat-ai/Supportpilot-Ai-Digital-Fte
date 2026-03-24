"""Structured AI support decision schema — produced by SupportDecisionEngine."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

_VALID_INTENTS = frozenset({
    "account", "technical", "billing", "complaint",
    "feature_request", "general", "urgent", "gratitude",
})
_VALID_CATEGORIES = frozenset({
    "technical", "billing", "account", "general", "complaint", "feature_request",
})
_VALID_PRIORITIES = frozenset({"low", "medium", "high", "urgent"})
_VALID_SENTIMENTS = frozenset({"positive", "neutral", "negative", "frustrated"})
_VALID_URGENCIES = frozenset({"low", "medium", "high"})


class SupportDecision(BaseModel):
    """Structured decision produced by the LLM for every customer message.

    All fields are validated and normalised — invalid enum values fall back to
    sensible defaults so the model never crashes the request.

    Example::

        {
          "reply": "No worries, I can help you reset your password ...",
          "intent": "account",
          "category": "account",
          "priority": "medium",
          "sentiment": "neutral",
          "urgency": "medium",
          "confidence": 0.87,
          "escalate": false,
          "escalation_reason": null
        }
    """

    reply: str = Field(..., description="Human-like helpful response to the customer")
    intent: str = Field(default="general", description="Detected intent category")
    category: str = Field(default="general", description="Support category for ticket routing")
    priority: str = Field(default="medium", description="Ticket priority level")
    sentiment: str = Field(default="neutral", description="Customer sentiment")
    urgency: str = Field(default="medium", description="Issue urgency level")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0, description="LLM confidence 0–1")
    escalate: bool = Field(default=False, description="Escalate to human agent")
    escalation_reason: Optional[str] = Field(default=None, description="Escalation reason")

    # ------------------------------------------------------------------
    # Validators — clamp/normalise every field so invalid model output
    # never propagates to callers.
    # ------------------------------------------------------------------

    @field_validator("confidence", mode="before")
    @classmethod
    def clamp_confidence(cls, v: object) -> float:
        try:
            return max(0.0, min(1.0, float(v)))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return 0.7

    @field_validator("intent", mode="before")
    @classmethod
    def validate_intent(cls, v: object) -> str:
        return str(v) if str(v) in _VALID_INTENTS else "general"

    @field_validator("category", mode="before")
    @classmethod
    def validate_category(cls, v: object) -> str:
        return str(v) if str(v) in _VALID_CATEGORIES else "general"

    @field_validator("priority", mode="before")
    @classmethod
    def validate_priority(cls, v: object) -> str:
        return str(v) if str(v) in _VALID_PRIORITIES else "medium"

    @field_validator("sentiment", mode="before")
    @classmethod
    def validate_sentiment(cls, v: object) -> str:
        return str(v) if str(v) in _VALID_SENTIMENTS else "neutral"

    @field_validator("urgency", mode="before")
    @classmethod
    def validate_urgency(cls, v: object) -> str:
        return str(v) if str(v) in _VALID_URGENCIES else "medium"
