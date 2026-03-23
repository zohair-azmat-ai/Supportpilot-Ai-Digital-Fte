"""
Gmail channel adapter — real implementation using the Gmail API.

Activation
----------
1. Create a Google Cloud project, enable the Gmail API.
2. Configure an OAuth2 Desktop App client (or Web App for production).
3. Run ``python scripts/gmail_auth.py`` to get a refresh token interactively.
4. Set in backend/.env:
       GMAIL_ENABLED=true
       GMAIL_CLIENT_ID=...
       GMAIL_CLIENT_SECRET=...
       GMAIL_REFRESH_TOKEN=...
       GMAIL_SENDER_ADDRESS=support@yourdomain.com

Two entry points
----------------
- **Webhook** (recommended for production):
  Gmail Pub/Sub push → POST /api/v1/channels/email/inbound
  The webhook payload is a base64-encoded notification containing a message ID.
  ``parse_inbound_pubsub(payload)`` fetches the full message from Gmail API.

- **Polling** (demo / local dev):
  ``GmailPollerWorker`` in workers/gmail_poller.py polls every GMAIL_POLL_INTERVAL_SECONDS
  for unread messages in INBOX, processes them, and marks them as read.
"""

from __future__ import annotations

import base64
import email as _email_lib
import logging
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Optional

from app.channels.base import BaseChannelAdapter, InboundMessage

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Priority inference from subject line
# ---------------------------------------------------------------------------

_URGENT_KEYWORDS = ("urgent", "critical", "emergency", "asap", "immediately", "outage", "down")
_HIGH_KEYWORDS = ("broken", "not working", "error", "bug", "failed", "can't", "cannot", "issue")


def _infer_priority(subject: str) -> str:
    lower = subject.lower()
    if any(kw in lower for kw in _URGENT_KEYWORDS):
        return "urgent"
    if any(kw in lower for kw in _HIGH_KEYWORDS):
        return "high"
    return "medium"


# ---------------------------------------------------------------------------
# Email parsing helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}")


def _parse_sender(raw: str) -> tuple[str, str]:
    """Extract (email, name) from a raw 'From' header like 'John Doe <john@example.com>'."""
    match = _EMAIL_RE.search(raw)
    email_addr = match.group(0) if match else raw.strip()
    # Extract display name — everything before the angle bracket
    name_part = raw.split("<")[0].strip().strip('"') if "<" in raw else email_addr
    return email_addr, name_part or email_addr


def _extract_plain_text(payload: dict) -> str:
    """Recursively extract plain-text body from a Gmail message payload dict."""
    mime_type = payload.get("mimeType", "")

    if mime_type == "text/plain":
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        return ""

    if mime_type in ("multipart/alternative", "multipart/mixed", "multipart/related"):
        for part in payload.get("parts", []):
            text = _extract_plain_text(part)
            if text:
                return text

    return ""


# ---------------------------------------------------------------------------
# Gmail API credential factory
# ---------------------------------------------------------------------------

def _get_credentials():
    """Build Google OAuth2 Credentials from environment variables.

    Requires:
        GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN

    Returns a google.oauth2.credentials.Credentials object with a valid
    access token (auto-refreshed from the stored refresh token).
    """
    from google.auth.transport.requests import Request  # type: ignore[import-untyped]
    from google.oauth2.credentials import Credentials  # type: ignore[import-untyped]

    from app.core.config import settings

    creds = Credentials(
        token=None,
        refresh_token=settings.GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.GMAIL_CLIENT_ID,
        client_secret=settings.GMAIL_CLIENT_SECRET,
        scopes=["https://www.googleapis.com/auth/gmail.modify"],
    )
    # Refresh to get a valid access token
    creds.refresh(Request())
    return creds


def _build_gmail_service():
    """Build an authenticated Gmail API service object."""
    from googleapiclient.discovery import build  # type: ignore[import-untyped]
    return build("gmail", "v1", credentials=_get_credentials(), cache_discovery=False)


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------


class EmailChannelAdapter(BaseChannelAdapter):
    """
    Gmail-based email channel adapter.

    Inbound (webhook): parse_inbound_pubsub(payload) for Gmail Pub/Sub notifications.
    Inbound (polling): fetch_unread_messages() for polling-based integration.
    Outbound: send_response() replies via Gmail API in the same thread.
    """

    channel_name = "email"

    # ------------------------------------------------------------------
    # Inbound — Pub/Sub webhook path
    # ------------------------------------------------------------------

    async def parse_inbound(self, payload: dict[str, Any]) -> InboundMessage:
        """Parse a Gmail Pub/Sub push notification body into an InboundMessage.

        Gmail Pub/Sub sends a JSON body:
        {
          "message": {
            "data": "<base64url-encoded JSON with emailAddress and historyId>",
            "messageId": "...",
            "publishTime": "..."
          },
          "subscription": "projects/.../subscriptions/..."
        }

        We use the historyId to fetch the latest message via Gmail API.
        """
        from app.core.config import settings

        if not settings.GMAIL_ENABLED:
            raise RuntimeError("Gmail integration is disabled (GMAIL_ENABLED=false)")

        try:
            service = _build_gmail_service()

            # Decode Pub/Sub data to get emailAddress and historyId
            raw_data = payload.get("message", {}).get("data", "")
            if raw_data:
                import json as _json
                decoded = base64.urlsafe_b64decode(raw_data + "==").decode("utf-8")
                notification = _json.loads(decoded)
                history_id = notification.get("historyId")

                if history_id:
                    # Fetch recent message history
                    history_resp = service.users().history().list(
                        userId="me",
                        startHistoryId=str(int(history_id) - 1),
                        historyTypes=["messageAdded"],
                        labelId="INBOX",
                    ).execute()

                    message_id = None
                    for record in history_resp.get("history", []):
                        for added in record.get("messagesAdded", []):
                            message_id = added["message"]["id"]
                            break
                        if message_id:
                            break

                    if message_id:
                        return await self._fetch_and_parse_message(service, message_id, payload)

            # Fallback: treat payload as a direct message object
            msg_id = payload.get("id") or payload.get("message", {}).get("id")
            if msg_id:
                return await self._fetch_and_parse_message(service, msg_id, payload)

            raise ValueError("Could not extract Gmail message ID from Pub/Sub payload")

        except Exception as exc:
            logger.error("EmailChannelAdapter.parse_inbound failed: %s", exc, exc_info=True)
            raise

    async def _fetch_and_parse_message(
        self, service: Any, message_id: str, raw_payload: dict
    ) -> InboundMessage:
        """Fetch a Gmail message by ID and convert to InboundMessage."""
        msg = service.users().messages().get(
            userId="me", id=message_id, format="full"
        ).execute()

        headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
        sender_raw = headers.get("From", "")
        subject = headers.get("Subject", "(no subject)")
        thread_id = msg.get("threadId")

        sender_email, sender_name = _parse_sender(sender_raw)
        body = _extract_plain_text(msg.get("payload", {}))

        # Trim email signatures and quoted replies (rough heuristic)
        body = _strip_email_signature(body)

        return InboundMessage(
            sender_name=sender_name,
            sender_email=sender_email,
            subject=subject,
            body=body or "(no body)",
            channel=self.channel_name,
            priority_hint=_infer_priority(subject),
            raw_payload={**raw_payload, "thread_id": thread_id, "message_id": message_id},
        )

    # ------------------------------------------------------------------
    # Inbound — Polling path (used by GmailPollerWorker)
    # ------------------------------------------------------------------

    def fetch_unread_messages(self) -> list[dict]:
        """Poll Gmail INBOX for unread messages. Returns raw Gmail message objects.

        Called by GmailPollerWorker. Uses a synchronous Gmail API call (the poller
        runs in a thread executor).

        Returns:
            List of Gmail message dicts with full payload.
        """
        from app.core.config import settings

        if not settings.GMAIL_ENABLED:
            return []

        try:
            service = _build_gmail_service()

            # Search for unread messages in INBOX only
            result = service.users().messages().list(
                userId="me",
                q="is:unread label:INBOX",
                maxResults=20,
            ).execute()

            messages = result.get("messages", [])
            full_messages = []
            for msg_ref in messages:
                full_msg = service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                ).execute()
                full_messages.append(full_msg)

            return full_messages

        except Exception as exc:
            logger.error("fetch_unread_messages failed: %s", exc)
            return []

    def parse_gmail_message_object(self, msg: dict) -> Optional[InboundMessage]:
        """Parse a raw Gmail message object (from fetch_unread_messages) into InboundMessage."""
        try:
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            sender_raw = headers.get("From", "")
            subject = headers.get("Subject", "(no subject)")
            thread_id = msg.get("threadId")
            message_id = msg.get("id")

            # Skip messages sent by us to avoid reply loops
            from app.core.config import settings
            if settings.GMAIL_SENDER_ADDRESS.lower() in sender_raw.lower():
                logger.debug("Skipping self-sent message: %s", message_id)
                return None

            sender_email, sender_name = _parse_sender(sender_raw)
            body = _extract_plain_text(msg.get("payload", {}))
            body = _strip_email_signature(body)

            return InboundMessage(
                sender_name=sender_name,
                sender_email=sender_email,
                subject=subject,
                body=body or "(no body)",
                channel=self.channel_name,
                priority_hint=_infer_priority(subject),
                raw_payload={"thread_id": thread_id, "message_id": message_id},
            )
        except Exception as exc:
            logger.error("parse_gmail_message_object failed: %s", exc)
            return None

    def mark_as_read(self, message_id: str) -> None:
        """Remove UNREAD label from a Gmail message after processing."""
        try:
            service = _build_gmail_service()
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            logger.debug("Marked message %s as read", message_id)
        except Exception as exc:
            logger.warning("Failed to mark message %s as read: %s", message_id, exc)

    # ------------------------------------------------------------------
    # Outbound
    # ------------------------------------------------------------------

    async def send_response(self, recipient: str, message: str, **kwargs: Any) -> bool:
        """Send a reply via Gmail API in the same email thread.

        Args:
            recipient  : Customer email address.
            message    : Plain-text reply body.
            **kwargs   :
                thread_id (str)  — Gmail thread ID to reply in.
                subject (str)    — Subject line for the reply.
                in_reply_to (str) — Message-ID header for proper threading.

        Returns:
            True if sent successfully, False on error.
        """
        from app.core.config import settings

        if not settings.GMAIL_ENABLED:
            logger.info(
                "Gmail disabled — skipping send_response to %s (message logged only)", recipient
            )
            return False

        try:
            thread_id: str | None = kwargs.get("thread_id")
            subject: str = kwargs.get("subject", "Re: Your Support Request")
            in_reply_to: str | None = kwargs.get("in_reply_to")

            if not subject.startswith("Re:"):
                subject = f"Re: {subject}"

            # Build MIME message
            mime_msg = MIMEMultipart("alternative")
            mime_msg["To"] = recipient
            mime_msg["From"] = settings.GMAIL_SENDER_ADDRESS
            mime_msg["Subject"] = subject
            if in_reply_to:
                mime_msg["In-Reply-To"] = in_reply_to
                mime_msg["References"] = in_reply_to

            # Plain text part
            mime_msg.attach(MIMEText(message, "plain", "utf-8"))

            raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("utf-8")
            body: dict[str, Any] = {"raw": raw}
            if thread_id:
                body["threadId"] = thread_id

            service = _build_gmail_service()
            sent = service.users().messages().send(userId="me", body=body).execute()
            logger.info(
                "Gmail reply sent | to=%s thread=%s msg_id=%s",
                recipient,
                thread_id,
                sent.get("id"),
            )
            return True

        except Exception as exc:
            logger.error(
                "EmailChannelAdapter.send_response failed | to=%s | %s", recipient, exc
            )
            return False


# ---------------------------------------------------------------------------
# Email cleanup helpers
# ---------------------------------------------------------------------------

_SIGNATURE_PATTERNS = [
    r"\n--\s*\n.*",               # -- signature delimiter
    r"\nSent from my .*",         # mobile clients
    r"\nOn .* wrote:\n.*",        # quoted reply preamble
    r"\n_{3,}\n.*",               # long underline separators
    r"\nGet Outlook for .*",      # Outlook footer
]
_SIGNATURE_RE = re.compile(
    "|".join(_SIGNATURE_PATTERNS),
    flags=re.DOTALL | re.IGNORECASE,
)


def _strip_email_signature(body: str) -> str:
    """Remove common email signature and quoted-reply patterns."""
    cleaned = _SIGNATURE_RE.sub("", body)
    return cleaned.strip()


# Module-level singleton
email_adapter = EmailChannelAdapter()
