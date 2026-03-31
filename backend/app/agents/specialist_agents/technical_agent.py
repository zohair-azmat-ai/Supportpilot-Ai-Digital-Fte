"""
TechnicalAgent — specialist for app crashes, performance, and data issues.

Handles intents: app_crash · slow_performance · data_missing · feature_missing

Phase 6 — interface defined, LLM specialisation to be wired in
when the multi-agent pipeline is activated.
"""

from __future__ import annotations

import logging
from typing import Any

from app.agents.specialist_agents.billing_agent import (
    SpecialistRequest,
    SpecialistResponse,
)

logger = logging.getLogger(__name__)

_TECHNICAL_SYSTEM_PREFIX = """\
You are SupportPilot Technical Specialist — an expert on application bugs,
performance degradation, data integrity, and feature issues.

Focus areas:
  • App crashes — gather error message, device/browser, repro steps
  • Slow performance — identify scope (all users vs one account)
  • Missing data — distinguish UI glitch from data loss
  • Feature not working — confirm expected vs actual behaviour

Ask targeted diagnostic questions. Keep replies ≤ 100 words.
"""


class TechnicalAgent:
    """Specialist agent for technical and product issues."""

    SPECIALIST_NAME = "technical"

    async def handle(
        self,
        request: SpecialistRequest,
        db: Any = None,
    ) -> SpecialistResponse:
        logger.info(
            "TechnicalAgent.handle: conversation=%s user=%s",
            request.conversation_id,
            request.user_id,
        )
        reply = self._keyword_response(request.message)
        return SpecialistResponse(
            reply=reply,
            specialist=self.SPECIALIST_NAME,
            escalate=False,
            confidence=0.85,
        )

    def _keyword_response(self, message: str) -> str:
        msg = message.lower()
        if any(k in msg for k in ("crash", "error", "500", "exception", "broken")):
            return (
                "Sorry to hear the app crashed. "
                "Can you share the error message you saw and the browser or device you're on? "
                "That'll help me pinpoint the cause quickly."
            )
        if any(k in msg for k in ("slow", "loading", "timeout", "hang", "freeze")):
            return (
                "Performance issues can stem from network conditions or server load. "
                "Is this happening on all pages or a specific section? "
                "And is it affecting just your account or everyone on your team?"
            )
        if any(k in msg for k in ("missing", "gone", "disappeared", "lost", "not showing")):
            return (
                "Let's figure out if this is a display issue or a data problem. "
                "Could you tell me what you expected to see and when it was last visible?"
            )
        return (
            "I'm the technical specialist here. "
            "Could you describe what's happening — any error messages, "
            "which feature is affected, and when it started?"
        )


# Module-level singleton
technical_agent = TechnicalAgent()
