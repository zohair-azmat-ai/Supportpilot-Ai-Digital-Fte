"""
Base channel adapter.

All channel adapters (web, email, WhatsApp) inherit from BaseChannelAdapter
and implement `parse_inbound`. The result is an InboundMessage — a
channel-agnostic representation of a support request that the SupportService
pipeline can process without knowing which channel it came from.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Shared inbound message schema
# ---------------------------------------------------------------------------


@dataclass
class InboundMessage:
    """
    Channel-agnostic representation of an inbound support message.

    All channel adapters normalise their raw payload into this structure
    before passing it to the SupportService.
    """

    # Who sent it
    sender_name: str
    sender_email: str

    # What they sent
    subject: str
    body: str

    # Which channel
    channel: str  # 'web' | 'email' | 'whatsapp'

    # Optional priority hint from the channel (e.g., email subject keywords)
    priority_hint: str = "medium"  # 'low' | 'medium' | 'high' | 'urgent'

    # Raw channel-specific payload preserved for audit / debugging
    raw_payload: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Abstract base adapter
# ---------------------------------------------------------------------------


class BaseChannelAdapter(ABC):
    """
    Abstract base class for all channel adapters.

    Subclasses implement:
    - `parse_inbound`  : normalise a raw channel payload → InboundMessage
    - `send_response`  : deliver a reply back through the same channel

    The adapter pattern keeps channel-specific logic fully isolated from the
    core SupportService pipeline. Adding a new channel only requires creating
    a new adapter subclass — nothing in the service layer changes.
    """

    channel_name: str = "base"

    @abstractmethod
    async def parse_inbound(self, payload: dict[str, Any]) -> InboundMessage:
        """
        Parse a raw channel payload into a normalised InboundMessage.

        Args:
            payload: Raw data received from the channel (webhook body,
                     form POST data, etc.).

        Returns:
            InboundMessage ready to be processed by SupportService.
        """
        ...

    @abstractmethod
    async def send_response(self, recipient: str, message: str, **kwargs: Any) -> bool:
        """
        Send a reply back to the customer through this channel.

        Args:
            recipient : Channel-specific address (email address, phone number, etc.)
            message   : The text response to send.
            **kwargs  : Channel-specific extras (subject line, thread ID, etc.)

        Returns:
            True if delivery succeeded, False otherwise.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} channel={self.channel_name!r}>"
