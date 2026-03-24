"""User-facing ticket routes."""

from __future__ import annotations

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db

logger = logging.getLogger(__name__)
from app.schemas.ticket import (
    CreateTicketRequest,
    TicketResponse,
    UpdateTicketRequest,
)
from app.services.ticket import ticket_service

router = APIRouter(prefix="/tickets", tags=["Tickets"])


@router.get(
    "",
    response_model=List[TicketResponse],
    summary="List tickets for the current user",
)
async def list_tickets(
    skip: int = 0,
    limit: int = 50,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[TicketResponse]:
    """Return all support tickets owned by the authenticated user."""
    tickets = await ticket_service.get_user_tickets(
        db, current_user.id, skip=skip, limit=limit
    )
    try:
        return [TicketResponse.model_validate(t) for t in tickets]
    except Exception:
        logger.exception("list_tickets: serialization error for user=%s", current_user.id)
        raise HTTPException(status_code=500, detail="Failed to serialize tickets")


@router.post(
    "",
    response_model=TicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new support ticket",
)
async def create_ticket(
    data: CreateTicketRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Submit a new support ticket."""
    ticket = await ticket_service.create_ticket(db, current_user.id, data)
    return TicketResponse.model_validate(ticket)


@router.get(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Get a specific ticket",
)
async def get_ticket(
    ticket_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Retrieve a ticket by ID (users can only view their own tickets)."""
    ticket = await ticket_service.get_ticket(db, ticket_id, current_user)
    return TicketResponse.model_validate(ticket)


@router.patch(
    "/{ticket_id}",
    response_model=TicketResponse,
    summary="Update a ticket",
)
async def update_ticket(
    ticket_id: str,
    data: UpdateTicketRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Partially update a ticket's fields (e.g., status or priority)."""
    ticket = await ticket_service.update_ticket(db, ticket_id, data, current_user)
    return TicketResponse.model_validate(ticket)
