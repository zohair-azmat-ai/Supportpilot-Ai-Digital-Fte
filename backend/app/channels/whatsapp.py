"""
WhatsApp channel adapter — Twilio integration (real implementation).

Activation
----------
1. Create a Twilio account at twilio.com.
2. Enable the WhatsApp Sandbox (console.twilio.com → Messaging → Senders → WhatsApp Sandbox)
   or request a production WhatsApp Business number.
3. Set webhook URL to: POST https://your-backend.railway.app/api/v1/channels/whatsapp/inbound
4. Set in backend/.env:
       TWILIO_ENABLED=true
       TWILIO_ACCOUNT_SID=ACxxxxxxxx
       TWILIO_AUTH_TOKEN=xxxxxxxx
       TWILIO_WHATSAPP_FROM=whatsapp:+14155238886  (sandbox) or your production number

Message window
--------------
WhatsApp allows freeform replies only within 24 hours of the customer's last message.
Outside this window, Meta requires approved message templates (HSM).
For demo/sandbox use, the 24-hour window is always open after the customer initiates.

Session continuity
------------------
Each sender phone number maps to a Customer via CustomerIdentifier(channel='whatsapp', value=phone).
One active Conversation per sender is maintained; new messages are appended to the open conversation.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from app.channels.base import BaseChannelAdapter, InboundMessage

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Priority inference
# ---------------------------------------------------------------------------

_URGENT_KEYWORDS = ("urgent", "emergency", "help", "asap", "critical", "now", "immediately")
_HIGH_KEYWORDS = ("broken", "not working", "error", "bug", "failed", "issue")


def _infer_priority(body: str) -> str:
    lower = body.lower()
    if any(kw in lower for kw in _URGENT_KEYWORDS):
        return "urgent"
    if any(kw in lower for kw in _HIGH_KEYWORDS):
        return "high"
    return "medium"


def _clean_phone(phone: str) -> str:
    """Strip the 'whatsapp:' prefix Twilio adds to sender numbers."""
    return phone.replace("whatsapp:", "").strip()


def _e164_to_display(phone: str) -> str:
    """Format E.164 phone number to a friendlier display form (+1 (555) 123-4567)."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
    return phone


# ---------------------------------------------------------------------------
# Twilio client factory
# ---------------------------------------------------------------------------

def _get_twilio_client():
    """Build an authenticated Twilio REST client from environment variables."""
    from twilio.rest import Client  # type: ignore[import-untyped]
    from app.core.config import settings

    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def validate_twilio_signature(
    auth_token: str, url: str, params: dict, signature: str
) -> bool:
    """Verify Twilio's HMAC-SHA1 webhook signature.

    Prevents spoofed webhook requests from being processed.
    """
    try:
        from twilio.request_validator import RequestValidator  # type: ignore[import-untyped]
        validator = RequestValidator(auth_token)
        return validator.validate(url, params, signature)
    except Exception as exc:
        logger.warning("Twilio signature validation error: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class WhatsAppChannelAdapter(BaseChannelAdapter):
    """
    Twilio WhatsApp channel adapter.

    Inbound: Twilio webhook POST (application/x-www-form-urlencoded).
    Outbound: Twilio messages.create() to WhatsApp number.
    """

    channel_name = "whatsapp"

    # ------------------------------------------------------------------
    # Inbound — primary parse path used by the webhook route
    # ------------------------------------------------------------------

    async def parse_inbound(self, payload: dict[str, Any]) -> InboundMessage:
        """Parse a Twilio WhatsApp webhook payload into an InboundMessage.

        Twilio sends form-encoded data with at minimum:
          From        : 'whatsapp:+1XXXXXXXXXX'
          Body        : message text
          ProfileName : sender display name (optional, set by WhatsApp user)
          NumMedia    : count of media attachments (0 for text-only)
          MessageSid  : unique Twilio message SID

        Args:
            payload: Dict of parsed form fields from the Twilio webhook body.

        Returns:
            Normalised InboundMessage.

        Raises:
            RuntimeError: If Twilio integration is not enabled.
            ValueError: If required fields are missing.
        """
        from app.core.config import settings

        if not settings.TWILIO_ENABLED:
            raise RuntimeError("WhatsApp integration is disabled (TWILIO_ENABLED=false)")

        sender_raw = payload.get("From", "")
        if not sender_raw:
            raise ValueError("Twilio webhook payload missing 'From' field")

        sender_phone = _clean_phone(sender_raw)
        # Use ProfileName if available; fall back to formatted phone number
        sender_name = payload.get("ProfileName", "") or _e164_to_display(sender_phone)
        body = payload.get("Body", "").strip()

        # Handle media messages gracefully (image, document, etc.)
        num_media = int(payload.get("NumMedia", 0))
        if not body and num_media > 0:
            media_types = [payload.get(f"MediaContentType{i}", "file") for i in range(num_media)]
            body = f"[Media attachment: {', '.join(media_types)}] — please describe your issue in text."

        if not body:
            body = "(no message body)"

        message_sid = payload.get("MessageSid", "")

        logger.info(
            "WhatsApp inbound | from=%s name=%s sid=%s",
            sender_phone,
            sender_name,
            message_sid,
        )

        return InboundMessage(
            sender_name=sender_name,
            # Synthetic email as system identifier (real contact is via phone)
            sender_email=f"{sender_phone.lstrip('+')}@whatsapp.supportpilot.internal",
            subject="WhatsApp Support Message",
            body=body,
            channel=self.channel_name,
            priority_hint=_infer_priority(body),
            raw_payload={
                **payload,
                "sender_phone": sender_phone,
                "message_sid": message_sid,
            },
        )

    # ------------------------------------------------------------------
    # Outbound
    # ------------------------------------------------------------------

    async def send_response(self, recipient: str, message: str, **kwargs: Any) -> bool:
        """Send a WhatsApp reply via the Twilio API.

        Args:
            recipient : Customer's phone number in E.164 format (+1XXXXXXXXXX).
                        Can also be passed as 'whatsapp:+1XXXXXXXXXX' — prefix is handled.
            message   : Reply text (WhatsApp max 1600 chars for freeform messages).
            **kwargs  : Optional — media_url (str) for image/document replies.

        Returns:
            True if Twilio accepted the message (HTTP 201), False on error.
        """
        from app.core.config import settings

        if not settings.TWILIO_ENABLED:
            logger.info(
                "Twilio disabled — skipping send_response to %s (message logged only)", recipient
            )
            return False

        # Normalise recipient to whatsapp: URI scheme
        if not recipient.startswith("whatsapp:"):
            to_whatsapp = f"whatsapp:{recipient}"
        else:
            to_whatsapp = recipient

        # Truncate to WhatsApp limit
        if len(message) > 1600:
            message = message[:1597] + "..."

        try:
            client = _get_twilio_client()
            create_kwargs: dict[str, Any] = {
                "from_": settings.TWILIO_WHATSAPP_FROM,
                "to": to_whatsapp,
                "body": message,
            }

            media_url: Optional[str] = kwargs.get("media_url")
            if media_url:
                create_kwargs["media_url"] = [media_url]

            msg = client.messages.create(**create_kwargs)

            logger.info(
                "WhatsApp reply sent | to=%s sid=%s status=%s",
                to_whatsapp,
                msg.sid,
                msg.status,
            )
            return True

        except Exception as exc:
            logger.error(
                "WhatsAppChannelAdapter.send_response failed | to=%s | %s",
                recipient,
                exc,
            )
            return False


# Module-level singleton
whatsapp_adapter = WhatsAppChannelAdapter()
