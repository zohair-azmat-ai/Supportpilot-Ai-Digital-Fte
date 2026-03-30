"""Message repository."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from app.models.message import Message
from app.repositories.base import BaseRepository


class MessageRepository(BaseRepository[Message]):
    """Data access layer for the Message model."""

    model = Message

    async def get_by_conversation(self, conversation_id: str) -> List[Message]:
        """Return all messages in a conversation ordered chronologically."""
        result = await self.db.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_message(
        self,
        conversation_id: str,
        sender_type: str,
        content: str,
        role: Optional[str] = None,
        channel: Optional[str] = None,
        intent: Optional[str] = None,
        ai_confidence: Optional[float] = None,
        sentiment: Optional[str] = None,
        urgency: Optional[str] = None,
        escalate: Optional[bool] = None,
        metadata: Optional[dict] = None,
    ) -> Message:
        """Create and persist a new message.

        Args:
            conversation_id: Parent conversation ID.
            sender_type: One of 'user', 'ai', or 'agent'.
            content: Message text content.
            role: Logical actor ('user', 'assistant'); defaults to sender_type.
            channel: Communication channel ('web', 'email', 'whatsapp'); defaults to 'web'.
            intent: Detected intent label (AI messages only).
            ai_confidence: Confidence score 0-1 (AI messages only).
            sentiment: Customer sentiment (AI messages only).
            urgency: Issue urgency level (AI messages only).
            escalate: Whether this message triggered escalation.
            metadata: Optional extra JSON payload.

        Returns:
            The persisted Message instance.
        """
        return await self.create(
            {
                "conversation_id": conversation_id,
                "sender_type": sender_type,
                "role": role if role is not None else sender_type,
                "channel": channel if channel is not None else "web",
                "content": content,
                "intent": intent,
                "ai_confidence": ai_confidence,
                "sentiment": sentiment,
                "urgency": urgency,
                "escalate": escalate,
                "metadata_": metadata,
            }
        )
