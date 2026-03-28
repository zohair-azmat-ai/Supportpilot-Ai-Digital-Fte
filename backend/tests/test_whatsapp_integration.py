from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.api.v1.routes.channels import whatsapp_inbound
from app.channels.whatsapp import WhatsAppSendResult, whatsapp_adapter
from app.core.config import settings


class FakeRequest:
    def __init__(
        self,
        form_payload: dict[str, str],
        url: str = "https://example.test/api/v1/channels/whatsapp/inbound",
        method: str = "POST",
    ) -> None:
        self._form_payload = form_payload
        self.url = url
        self.method = method

    async def form(self) -> dict[str, str]:
        return self._form_payload


class WhatsAppIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_parse_inbound_normalizes_phone_and_media(self) -> None:
        with patch.object(settings, "TWILIO_ACCOUNT_SID", "AC123"), patch.object(
            settings, "TWILIO_AUTH_TOKEN", "secret"
        ), patch.object(settings, "TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886"):
            inbound = await whatsapp_adapter.parse_inbound(
                {
                    "From": "whatsapp:+15551234567",
                    "ProfileName": "Casey",
                    "Body": "",
                    "NumMedia": "1",
                    "MediaContentType0": "image/jpeg",
                    "MessageSid": "SM123",
                }
            )

        self.assertEqual(inbound.channel, "whatsapp")
        self.assertEqual(inbound.sender_phone, "+15551234567")
        self.assertEqual(inbound.thread_id, "+15551234567")
        self.assertEqual(inbound.external_id, "SM123")
        self.assertIn("Media attachment", inbound.body)

    async def test_whatsapp_webhook_returns_503_when_twilio_missing(self) -> None:
        request = FakeRequest({"From": "whatsapp:+15551234567", "Body": "Need help"})
        with patch.object(settings, "TWILIO_ACCOUNT_SID", ""), patch.object(
            settings, "TWILIO_AUTH_TOKEN", ""
        ), patch.object(settings, "TWILIO_WHATSAPP_FROM", ""):
            with self.assertRaises(HTTPException) as ctx:
                await whatsapp_inbound(request=request, db=AsyncMock(), x_twilio_signature="")

        self.assertEqual(ctx.exception.status_code, 503)

    async def test_send_response_reports_missing_credentials_without_crashing(self) -> None:
        with patch.object(settings, "TWILIO_ACCOUNT_SID", ""), patch.object(
            settings, "TWILIO_AUTH_TOKEN", ""
        ), patch.object(settings, "TWILIO_WHATSAPP_FROM", ""):
            result = await whatsapp_adapter.send_response_with_result(
                "+15551234567",
                "Hello from SupportPilot",
            )

        self.assertIsInstance(result, WhatsAppSendResult)
        self.assertFalse(result.success)
        self.assertIn("not fully configured", result.error or "")


class FirstContactEscalationTests(unittest.IsolatedAsyncioTestCase):
    """Verify that the escalation engine never escalates on first contact
    unless a hard rule (security / legal / explicit human request) applies."""

    async def test_first_contact_blocks_llm_escalation(self) -> None:
        """LLM choosing escalate=True on turn 1 must be suppressed."""
        from app.ai.escalation_engine import escalation_engine
        from app.ai.context_builder import ConversationContext
        from app.schemas.ai_decision import SupportDecision

        ctx = ConversationContext(is_first_contact=True, message_count_in_session=0)
        decision = SupportDecision(
            reply="Let me help you with that.",
            intent="account",
            category="account",
            priority="medium",
            sentiment="neutral",
            urgency="medium",
            confidence=0.8,
            escalate=True,
            escalation_reason="Open ticket exists — may be ongoing",
        )

        result = escalation_engine.evaluate(
            context=ctx,
            llm_decision=decision,
            user_message="my account is not working",
        )

        self.assertFalse(result.escalate, "First-contact must NOT escalate")
        self.assertEqual(result.escalation_level, "none")

    async def test_first_contact_hard_rule_still_escalates(self) -> None:
        """Hard rules (security keyword) must override first-contact protection."""
        from app.ai.escalation_engine import escalation_engine
        from app.ai.context_builder import ConversationContext
        from app.schemas.ai_decision import SupportDecision

        ctx = ConversationContext(is_first_contact=True, message_count_in_session=0)
        decision = SupportDecision(
            reply="Let me look into that.",
            intent="account",
            category="account",
            priority="medium",
            sentiment="neutral",
            urgency="medium",
            confidence=0.8,
            escalate=False,
        )

        result = escalation_engine.evaluate(
            context=ctx,
            llm_decision=decision,
            user_message="I think my account was hacked",
        )

        self.assertTrue(result.escalate, "Security keyword must escalate even on first contact")
        self.assertEqual(result.escalation_cause, "security")

    async def test_context_builder_no_repeated_issue_on_first_contact(self) -> None:
        """First-contact messages with 'not working' must NOT set repeated_issue."""
        from app.ai.context_builder import context_builder

        ctx = await context_builder.build(
            db=None,
            user_id="test-user-123",
            user_message="my login is not working",
            conversation_history=[],  # empty = first contact
        )

        self.assertTrue(ctx.is_first_contact)
        self.assertFalse(ctx.repeated_issue, "'not working' on first message must not set repeated_issue")
        self.assertEqual(ctx.previous_failed_attempts, 0)

    async def test_context_builder_repeated_issue_on_second_turn(self) -> None:
        """repeated_issue should still be detectable on subsequent turns."""
        from app.ai.context_builder import context_builder

        history = [
            {"sender_type": "user", "content": "my login is not working"},
            {"sender_type": "ai", "content": "Have you tried resetting your password?"},
        ]
        ctx = await context_builder.build(
            db=None,
            user_id="test-user-123",
            user_message="still not working after reset",
            conversation_history=history,
        )

        self.assertFalse(ctx.is_first_contact)
        # "still not working" keywords + prior turn → repeated_issue should be detected
        self.assertTrue(ctx.repeated_issue)

    async def test_sanitize_first_contact_reply_removes_bad_phrases(self) -> None:
        """Reply sanitizer must strip 'still facing', 'ongoing issue', etc."""
        from app.ai.agent import SupportAgent

        dirty = (
            "I can see you're still facing this issue. "
            "Regarding your ongoing issue with login, let me assist you."
        )
        clean = SupportAgent._sanitize_first_contact_reply(dirty)

        self.assertNotIn("still facing", clean)
        self.assertNotIn("ongoing issue", clean)


if __name__ == "__main__":
    unittest.main()
