"""
Web channel adapter.

STATUS: Live — fully operational.

Handles support requests submitted via:
- The public web support form  (POST /api/v1/support/submit)
- Authenticated customer chat  (POST /api/v1/conversations/{id}/messages)

This adapter is thin because the web channel payloads are already
well-structured JSON from the frontend. Its main job is to normalise
the form data into an InboundMessage and provide the no-op send_response
(web replies are returned directly in the HTTP response, not pushed).
"""

from __future__ import annotations

import logging
from typing import Any

from app.channels.base import BaseChannelAdapter, InboundMessage

logger = logging.getLogger(__name__)


class WebChannelAdapter(BaseChannelAdapter):
    """
    Adapter for the web support form and authenticated chat channel.

    Inbound payloads come from:
        SupportFormRequest  (name, email, subject, message, category, priority)
        SendMessageRequest  (content — within an existing conversation)
    """

    channel_name = "web"

    async def parse_inbound(self, payload: dict[str, Any]) -> InboundMessage:
        """
        Normalise a web form / chat payload into an InboundMessage.

        Expected payload keys:
            name     : str
            email    : str
            subject  : str  (optional for chat messages)
            message  : str
            priority : str  (optional, default 'medium')
        """
        return InboundMessage(
            sender_name=payload.get("name", "Web User"),
            sender_email=payload.get("email", ""),
            subject=payload.get("subject", "Support Request"),
            body=payload.get("message", ""),
            channel=self.channel_name,
            priority_hint=payload.get("priority", "medium"),
            raw_payload=payload,
        )

    async def send_response(self, recipient: str, message: str, **kwargs: Any) -> bool:
        """
        No-op for the web channel — responses are returned in the HTTP response body.

        The SupportService / MessageService returns the AI reply directly to
        the caller. There is nothing to push asynchronously.
        """
        logger.debug(
            "WebChannelAdapter.send_response: no-op (response returned via HTTP). "
            "recipient=%r",
            recipient,
        )
        return True


# Module-level singleton
web_adapter = WebChannelAdapter()
