"""
Channel adapters package.

Each adapter normalises an inbound support message from a specific channel
(web, email, WhatsApp) into the shared InboundMessage schema before handing
off to the SupportService pipeline.

Active channels
---------------
- web      : Live — web support form and authenticated chat

Scaffolded channels (credentials required to activate)
-------------------------------------------------------
- email    : Gmail API OAuth2 + webhook ingest
- whatsapp : Twilio WhatsApp Business API + webhook ingest
"""

from app.channels.base import BaseChannelAdapter, InboundMessage

__all__ = ["BaseChannelAdapter", "InboundMessage"]
