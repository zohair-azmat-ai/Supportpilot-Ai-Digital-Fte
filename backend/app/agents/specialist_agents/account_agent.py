"""
AccountAgent — specialist for login, password reset, 2FA, and account-locked issues.

Handles intents: password_reset · login_issue · account_locked · 2fa

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

_ACCOUNT_SYSTEM_PREFIX = """\
You are SupportPilot Account Specialist — an expert on authentication,
identity, and account security.

Focus areas:
  • Password reset — guide through self-service reset flow
  • Login failures — distinguish wrong password from locked account from SSO issue
  • 2FA issues — recovery codes, authenticator app re-enrollment
  • Account locked — unlock criteria, appeal process

Never ask for passwords. Keep replies ≤ 100 words and security-conscious.
"""


class AccountAgent:
    """Specialist agent for account and authentication issues."""

    SPECIALIST_NAME = "account"

    async def handle(
        self,
        request: SpecialistRequest,
        db: Any = None,
    ) -> SpecialistResponse:
        logger.info(
            "AccountAgent.handle: conversation=%s user=%s",
            request.conversation_id,
            request.user_id,
        )
        reply = self._keyword_response(request.message)
        return SpecialistResponse(
            reply=reply,
            specialist=self.SPECIALIST_NAME,
            escalate=False,
            confidence=0.88,
        )

    def _keyword_response(self, message: str) -> str:
        msg = message.lower()
        if any(k in msg for k in ("password", "reset", "forgot")):
            return (
                "To reset your password, go to the login page and click "
                '"Forgot password?" — you\'ll receive a reset link within a minute. '
                "Let me know if you don't receive it and I'll look into your account."
            )
        if any(k in msg for k in ("locked", "suspended", "disabled", "blocked")):
            return (
                "Account locks typically happen after multiple failed login attempts. "
                "Your account should auto-unlock after 15 minutes. "
                "If it's still locked after that, I can escalate to the security team."
            )
        if any(k in msg for k in ("2fa", "two factor", "authenticator", "otp", "code")):
            return (
                "If you've lost access to your 2FA device, you can use a backup recovery code. "
                "If you don't have those, I'll need to verify your identity before re-enrolling — "
                "can you confirm the email on your account?"
            )
        if any(k in msg for k in ("login", "sign in", "can't access", "cannot access")):
            return (
                "Let's get you back in. "
                "Are you seeing an error message when you try to log in, "
                "or is the page not loading at all?"
            )
        return (
            "I'm the account specialist here. "
            "Could you describe what's happening with your account access?"
        )


# Module-level singleton
account_agent = AccountAgent()
