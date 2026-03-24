"""Admin-only routes."""

from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin

logger = logging.getLogger(__name__)
from app.repositories.conversation import ConversationRepository
from app.repositories.user import UserRepository
from app.repositories.ticket import TicketRepository
from app.schemas.admin import AdminStatsResponse
from app.schemas.auth import UserResponse
from app.schemas.conversation import ConversationResponse
from app.schemas.ticket import TicketResponse, UpdateTicketRequest
from app.services.ticket import ticket_service

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/stats",
    response_model=AdminStatsResponse,
    summary="Get platform-wide statistics",
)
async def get_stats(
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> AdminStatsResponse:
    """Return aggregated statistics for the admin dashboard."""
    user_repo = UserRepository(db)
    ticket_repo = TicketRepository(db)
    conv_repo = ConversationRepository(db)

    try:
        total_users = await user_repo.count_users()
        total_tickets = await ticket_repo.count_total()
        open_tickets = await ticket_repo.count_by_status("open")
        total_conversations = await conv_repo.count_total()
        active_conversations = await conv_repo.count_active()
        resolved_today = await ticket_repo.count_resolved_today()
    except Exception as exc:
        logger.error("Failed to fetch admin stats: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stats temporarily unavailable. Please try again.",
        ) from exc

    return AdminStatsResponse(
        total_users=total_users,
        total_tickets=total_tickets,
        open_tickets=open_tickets,
        total_conversations=total_conversations,
        active_conversations=active_conversations,
        resolved_today=resolved_today,
    )


@router.get(
    "/tickets",
    response_model=List[TicketResponse],
    summary="List all tickets (admin, filterable)",
)
async def list_all_tickets(
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[TicketResponse]:
    """Return a paginated list of all tickets, with optional status/priority filters."""
    tickets = await ticket_service.get_all_tickets(
        db,
        skip=skip,
        limit=limit,
        status_filter=status,
        priority_filter=priority,
    )
    return [TicketResponse.model_validate(t) for t in tickets]


@router.patch(
    "/tickets/{ticket_id}",
    response_model=TicketResponse,
    summary="Update any ticket (admin)",
)
async def admin_update_ticket(
    ticket_id: str,
    data: UpdateTicketRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> TicketResponse:
    """Allow an admin to update any ticket regardless of ownership."""
    ticket = await ticket_service.update_ticket(db, ticket_id, data, admin)
    return TicketResponse.model_validate(ticket)


@router.get(
    "/conversations",
    response_model=List[ConversationResponse],
    summary="List all conversations (admin)",
)
async def list_all_conversations(
    skip: int = 0,
    limit: int = 50,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationResponse]:
    """Return a paginated list of all conversations in the system."""
    repo = ConversationRepository(db)
    convs = await repo.get_all_paginated(skip=skip, limit=limit)
    return [ConversationResponse.model_validate(c) for c in convs]


@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List all users (admin)",
)
async def list_all_users(
    skip: int = 0,
    limit: int = 50,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[UserResponse]:
    """Return a paginated list of all registered users."""
    repo = UserRepository(db)
    users = await repo.get_all_users(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]
