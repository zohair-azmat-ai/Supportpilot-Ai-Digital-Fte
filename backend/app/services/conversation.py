"""Conversation service."""

from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.user import User
from app.repositories.conversation import ConversationRepository


class ConversationService:
    """Business logic for conversation management."""

    async def create_conversation(
        self,
        db: AsyncSession,
        user_id: str,
        channel: str = "web",
        subject: Optional[str] = None,
    ) -> Conversation:
        """Create a new conversation for a user.

        Args:
            db: Active database session.
            user_id: ID of the owning user.
            channel: Communication channel ('web', 'email', 'whatsapp').
            subject: Optional conversation subject.

        Returns:
            The newly created Conversation.
        """
        repo = ConversationRepository(db)
        return await repo.create(
            {
                "user_id": user_id,
                "channel": channel,
                "subject": subject,
                "status": "active",
            }
        )

    async def get_user_conversations(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Conversation]:
        """Return all conversations belonging to a user."""
        repo = ConversationRepository(db)
        return await repo.get_by_user(user_id, skip=skip, limit=limit)

    async def get_conversation_detail(
        self,
        db: AsyncSession,
        conversation_id: str,
        current_user: User,
    ) -> Conversation:
        """Fetch a conversation with its messages.

        Admins can access any conversation; regular users can only access their own.

        Raises:
            HTTPException 404: If the conversation does not exist.
            HTTPException 403: If a non-admin user requests another user's conversation.
        """
        repo = ConversationRepository(db)
        conversation = await repo.get_with_messages(conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        if current_user.role != "admin" and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this conversation",
            )

        return conversation

    async def close_conversation(
        self,
        db: AsyncSession,
        conversation_id: str,
        current_user: User,
    ) -> Conversation:
        """Close a conversation (set status to 'closed').

        Raises:
            HTTPException 404: If the conversation is not found.
            HTTPException 403: If a non-admin attempts to close another user's conversation.
        """
        repo = ConversationRepository(db)
        conversation = await repo.get(conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        if current_user.role != "admin" and conversation.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to close this conversation",
            )

        updated = await repo.update(conversation_id, {"status": "closed"})
        return updated  # type: ignore[return-value]


conversation_service = ConversationService()
