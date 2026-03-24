"""Conversation repository."""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models.conversation import Conversation
from app.models.message import Message
from app.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[Conversation]):
    """Data access layer for the Conversation model."""

    model = Conversation

    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Conversation]:
        """Return paginated conversations belonging to a specific user."""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_with_messages(self, id: str) -> Optional[Conversation]:
        """Retrieve a conversation and eagerly load its messages."""
        result = await self.db.execute(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == id)
        )
        return result.scalars().first()

    async def count_active(self) -> int:
        """Return the number of conversations with status 'active'."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Conversation)
            .where(Conversation.status == "active")
        )
        return result.scalar_one_or_none() or 0

    async def count_total(self) -> int:
        """Return the total number of conversations."""
        result = await self.db.execute(
            select(func.count()).select_from(Conversation)
        )
        return result.scalar_one_or_none() or 0

    async def get_all_paginated(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Conversation]:
        """Return all conversations ordered by last update time."""
        result = await self.db.execute(
            select(Conversation)
            .order_by(Conversation.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_thread_id(self, thread_id: str) -> Optional[Conversation]:
        """Return the most recent conversation with this thread_id.

        Used by email (Gmail thread ID) and WhatsApp (sender phone) to resume
        an existing conversation thread rather than creating a new one.
        """
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.thread_id == thread_id)
            .order_by(Conversation.updated_at.desc())
        )
        return result.scalars().first()

    async def get_active_by_user_channel(
        self,
        user_id: str,
        channel: str,
    ) -> Optional[Conversation]:
        """Return the most recently updated active conversation for a user+channel pair.

        More reliable than a linear scan through get_by_user() when the user
        has multiple conversations.
        """
        result = await self.db.execute(
            select(Conversation)
            .where(
                Conversation.user_id == user_id,
                Conversation.channel == channel,
                Conversation.status == "active",
            )
            .order_by(Conversation.updated_at.desc())
        )
        return result.scalars().first()
