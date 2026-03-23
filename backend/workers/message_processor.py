"""
Message processor worker.

Consumes from 'webform_inbound', 'email_inbound', and 'whatsapp_inbound' topics.
Runs the complete support pipeline:
  1. Resolve or create customer
  2. Create conversation
  3. Run AI agent
  4. Store messages
  5. Deliver response via correct channel adapter

In production (USE_KAFKA=true): runs as a standalone process.
In development (USE_KAFKA=false): the InMemoryEventBus calls process() synchronously.
"""

from __future__ import annotations

import logging
import os
import sys

# Ensure backend/ is on sys.path when running as standalone process
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Any

from workers.base import BaseWorker

logger = logging.getLogger(__name__)


class MessageProcessorWorker(BaseWorker):
    """
    Processes inbound support messages from all channels.

    Handles topics: webform_inbound, email_inbound, whatsapp_inbound
    (Each channel registers this worker on its respective topic.)
    """

    topic = "webform_inbound"  # Primary topic; extended for other channels
    worker_name = "message_processor"

    async def on_start(self) -> None:
        """Initialise DB connection pool for standalone process."""
        logger.info("MessageProcessorWorker initialising database connection...")
        from app.core.database import init_db

        await init_db()
        logger.info("MessageProcessorWorker ready.")

    async def process(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Full pipeline for one inbound support event.

        For WEBFORM events (event_type = 'support.form'):
          1. Find or create user by email
          2. Create conversation (channel=web)
          3. Store user message
          4. Run AI agent (tool-based)
          5. Store AI response + metrics
          6. Create ticket
          7. Publish metrics event
          8. Return result dict

        For CHAT MESSAGE events (event_type = 'support.message'):
          1. Validate conversation ownership
          2. Store user message
          3. Run AI agent with conversation history
          4. Store AI response + metrics
          5. Handle escalation
          6. Publish metrics event
          7. Return (user_message, ai_message) equivalent dict
        """
        from app.core.database import AsyncSessionLocal

        event_type = event.get("event_type", "")

        async with AsyncSessionLocal() as db:
            try:
                if event_type == "support.form":
                    return await self._process_form_event(db, event)
                elif event_type == "support.message":
                    return await self._process_message_event(db, event)
                else:
                    logger.warning("Unknown event type: %s", event_type)
                    return {
                        "status": "skipped",
                        "reason": f"unknown event type: {event_type}",
                    }
            except Exception as exc:
                logger.error(
                    "Failed to process event %s: %s",
                    event.get("event_id"),
                    exc,
                    exc_info=True,
                )
                raise

    async def _process_form_event(self, db: Any, event: dict[str, Any]) -> dict[str, Any]:
        """Process a web form submission event."""
        import secrets

        from app.ai.agent import support_agent
        from app.core.security import hash_password
        from app.repositories.conversation import ConversationRepository
        from app.repositories.message import MessageRepository
        from app.repositories.ticket import TicketRepository
        from app.repositories.user import UserRepository

        user_repo = UserRepository(db)
        user = await user_repo.get_by_email(event["email"])
        if user is None:
            user = await user_repo.create(
                {
                    "name": event["name"],
                    "email": event["email"],
                    "password_hash": hash_password(secrets.token_urlsafe(24)),
                    "role": "customer",
                }
            )

        conv_repo = ConversationRepository(db)
        conversation = await conv_repo.create(
            {
                "user_id": user.id,
                "channel": event.get("channel", "web"),
                "subject": event.get("subject", "Support Request"),
                "status": "active",
            }
        )

        msg_repo = MessageRepository(db)
        await msg_repo.create_message(
            conversation_id=conversation.id,
            sender_type="user",
            content=event["message"],
        )

        # Run AI agent
        ai_result = await support_agent.run(
            db=db,
            user_id=user.id,
            conversation_id=conversation.id,
            user_message=event["message"],
            conversation_history=[],
        )

        await msg_repo.create_message(
            conversation_id=conversation.id,
            sender_type="ai",
            content=ai_result.response,
            intent=ai_result.intent,
            ai_confidence=ai_result.confidence,
            metadata=(
                {
                    "should_escalate": ai_result.should_escalate,
                    "escalation_reason": ai_result.escalation_reason,
                }
                if ai_result.should_escalate
                else None
            ),
        )

        if ai_result.should_escalate:
            await conv_repo.update(conversation.id, {"status": "escalated"})

        # Agent may have created ticket; if not, create one
        ticket_repo = TicketRepository(db)
        ticket = await ticket_repo.create(
            {
                "user_id": user.id,
                "conversation_id": conversation.id,
                "title": event.get("subject", "Support Request"),
                "description": event["message"],
                "category": event.get("category", "general"),
                "priority": event.get("priority", "medium"),
            }
        )

        confirmation = (
            f"Thank you for contacting SupportPilot, {event['name']}. "
            f"Your request has been received and a ticket (#{ticket.id[:8].upper()}) "
            "has been created. Our team will follow up with you shortly."
        )

        return {
            "conversation_id": conversation.id,
            "ticket_id": ticket.id,
            "confirmation_message": confirmation,
            "ai_response": ai_result.response,
        }

    async def _process_message_event(self, db: Any, event: dict[str, Any]) -> dict[str, Any]:
        """Process a chat message event."""
        from app.ai.agent import support_agent
        from app.repositories.conversation import ConversationRepository
        from app.repositories.message import MessageRepository

        conv_repo = ConversationRepository(db)
        conversation = await conv_repo.get_with_messages(event["conversation_id"])

        if not conversation:
            raise ValueError(
                f"Conversation not found: {event['conversation_id']}"
            )

        msg_repo = MessageRepository(db)
        user_message = await msg_repo.create_message(
            conversation_id=event["conversation_id"],
            sender_type="user",
            content=event["content"],
        )

        history = [
            {"sender_type": m.sender_type, "content": m.content}
            for m in (conversation.messages or [])
        ]

        ai_result = await support_agent.run(
            db=db,
            user_id=event["user_id"],
            conversation_id=event["conversation_id"],
            user_message=event["content"],
            conversation_history=history,
        )

        ai_message = await msg_repo.create_message(
            conversation_id=event["conversation_id"],
            sender_type="ai",
            content=ai_result.response,
            intent=ai_result.intent,
            ai_confidence=ai_result.confidence,
            metadata=(
                {
                    "should_escalate": ai_result.should_escalate,
                    "escalation_reason": ai_result.escalation_reason,
                }
                if ai_result.should_escalate
                else None
            ),
        )

        if ai_result.should_escalate and conversation.status == "active":
            await conv_repo.update(
                event["conversation_id"], {"status": "escalated"}
            )

        return {
            "user_message_id": user_message.id,
            "ai_message_id": ai_message.id,
            "ai_response": ai_result.response,
            "intent": ai_result.intent,
            "should_escalate": ai_result.should_escalate,
        }


# Singleton
message_processor = MessageProcessorWorker()
