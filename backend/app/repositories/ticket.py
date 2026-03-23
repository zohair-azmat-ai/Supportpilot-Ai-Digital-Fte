"""Ticket repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select

from app.models.ticket import Ticket
from app.repositories.base import BaseRepository


class TicketRepository(BaseRepository[Ticket]):
    """Data access layer for the Ticket model."""

    model = Ticket

    async def get_by_user(
        self,
        user_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Ticket]:
        """Return paginated tickets owned by a specific user."""
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Ticket]:
        """Return paginated tickets with a specific status."""
        result = await self.db.execute(
            select(Ticket)
            .where(Ticket.status == status)
            .order_by(Ticket.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_status(self, status: str) -> int:
        """Return the count of tickets with the given status."""
        result = await self.db.execute(
            select(func.count())
            .select_from(Ticket)
            .where(Ticket.status == status)
        )
        return result.scalar_one()

    async def count_total(self) -> int:
        """Return the total number of tickets."""
        result = await self.db.execute(
            select(func.count()).select_from(Ticket)
        )
        return result.scalar_one()

    async def count_resolved_today(self) -> int:
        """Return the number of tickets resolved today (UTC)."""
        today_start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        result = await self.db.execute(
            select(func.count())
            .select_from(Ticket)
            .where(Ticket.status == "resolved")
            .where(Ticket.updated_at >= today_start)
        )
        return result.scalar_one()

    async def get_all_paginated(
        self,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[Ticket]:
        """Return paginated tickets with optional filters.

        Args:
            skip: Number of records to skip.
            limit: Maximum records to return.
            status: Optional status filter.
            priority: Optional priority filter.
        """
        query = select(Ticket).order_by(Ticket.created_at.desc())

        if status is not None:
            query = query.where(Ticket.status == status)
        if priority is not None:
            query = query.where(Ticket.priority == priority)

        result = await self.db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())
