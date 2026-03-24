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
    ) -> None:
        self._form_payload = form_payload
        self.url = url

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


if __name__ == "__main__":
    unittest.main()
