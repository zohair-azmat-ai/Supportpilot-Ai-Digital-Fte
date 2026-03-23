"""Ticket service."""

from __future__ import annotations

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket
from app.models.user import User
from app.repositories.ticket import TicketRepository
from app.schemas.ticket import CreateTicketRequest, UpdateTicketRequest


class TicketService:
    """Business logic for ticket management."""

    async def create_ticket(
        self,
        db: AsyncSession,
        user_id: str,
        data: CreateTicketRequest,
    ) -> Ticket:
        """Create a new support ticket.

        Args:
            db: Active database session.
            user_id: ID of the ticket owner.
            data: Validated creation payload.

        Returns:
            The newly created Ticket.
        """
        repo = TicketRepository(db)
        return await repo.create(
            {
                "user_id": user_id,
                "conversation_id": data.conversation_id,
                "title": data.title,
                "description": data.description,
                "category": data.category,
                "priority": data.priority,
            }
        )

    async def get_user_tickets(
        self,
        db: AsyncSession,
        user_id: str,
        skip: int = 0,
        limit: int = 50,
    ) -> List[Ticket]:
        """Return all tickets for a specific user."""
        repo = TicketRepository(db)
        return await repo.get_by_user(user_id, skip=skip, limit=limit)

    async def get_ticket(
        self,
        db: AsyncSession,
        ticket_id: str,
        current_user: User,
    ) -> Ticket:
        """Fetch a ticket by ID.

        Regular users can only access their own tickets; admins can access any.

        Raises:
            HTTPException 404: If the ticket does not exist.
            HTTPException 403: Ownership violation for non-admin users.
        """
        repo = TicketRepository(db)
        ticket = await repo.get(ticket_id)

        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found",
            )

        if current_user.role != "admin" and ticket.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to view this ticket",
            )

        return ticket

    async def update_ticket(
        self,
        db: AsyncSession,
        ticket_id: str,
        data: UpdateTicketRequest,
        current_user: User,
    ) -> Ticket:
        """Partially update a ticket.

        Raises:
            HTTPException 404: If the ticket is not found.
            HTTPException 403: If a non-admin attempts to update another user's ticket.
        """
        repo = TicketRepository(db)
        ticket = await repo.get(ticket_id)

        if ticket is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found",
            )

        if current_user.role != "admin" and ticket.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to update this ticket",
            )

        update_data = data.model_dump(exclude_none=True)
        updated = await repo.update(ticket_id, update_data)
        return updated  # type: ignore[return-value]

    async def get_all_tickets(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        status_filter: Optional[str] = None,
        priority_filter: Optional[str] = None,
    ) -> List[Ticket]:
        """Return a paginated list of all tickets (admin use)."""
        repo = TicketRepository(db)
        return await repo.get_all_paginated(
            skip=skip,
            limit=limit,
            status=status_filter,
            priority=priority_filter,
        )


ticket_service = TicketService()
