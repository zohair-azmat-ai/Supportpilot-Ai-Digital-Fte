"""Admin-only routes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, require_admin

logger = logging.getLogger(__name__)
from app.repositories.agent_metrics import AgentMetricsRepository
from app.repositories.conversation import ConversationRepository
from app.repositories.user import UserRepository
from app.repositories.ticket import TicketRepository
from app.schemas.admin import AdminStatsResponse
from app.schemas.auth import UserResponse
from app.schemas.conversation import ConversationResponse
from app.schemas.ticket import TicketResponse, UpdateTicketRequest
from app.services.event_logger import event_logger
from app.services.ticket import ticket_service

router = APIRouter(prefix="/admin", tags=["Admin"])


class ConversationInsightResponse(BaseModel):
    """Latest AI reasoning snapshot for one conversation."""
    # From latest AgentMetrics row (None when no metrics recorded yet)
    routed_agent: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    escalated: bool = False
    escalation_reason: Optional[str] = None
    escalation_level: Optional[str] = None
    escalation_cause: Optional[str] = None
    urgency: Optional[str] = None
    sentiment: Optional[str] = None
    response_time_ms: Optional[float] = None
    # From latest Ticket linked to this conversation (None when no ticket)
    ticket_id: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[str] = None
    ticket_status: Optional[str] = None


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


@router.get(
    "/conversations/{conversation_id}/insight",
    response_model=ConversationInsightResponse,
    summary="Latest AI insight for a conversation (admin)",
)
async def get_conversation_insight(
    conversation_id: str,
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ConversationInsightResponse:
    """Return the latest AI agent reasoning snapshot for a conversation.

    Combines the most recent AgentMetrics record with the most recent
    Ticket linked to the conversation.  Returns a 404 when no metrics
    have been recorded yet (e.g. the conversation has no AI reply).
    """
    metrics_repo = AgentMetricsRepository(db)
    all_metrics = await metrics_repo.get_by_conversation(conversation_id)

    if not all_metrics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No AI metrics recorded for this conversation yet.",
        )

    m = all_metrics[-1]  # latest record (list is ordered asc by created_at)

    ticket_repo = TicketRepository(db)
    tickets = await ticket_repo.get_by_conversation(conversation_id)
    t = tickets[-1] if tickets else None

    return ConversationInsightResponse(
        routed_agent=m.routed_agent,
        intent=m.intent_detected,
        confidence=m.confidence_score,
        escalated=bool(m.was_escalated),
        escalation_reason=m.escalation_reason,
        escalation_level=m.escalation_level,
        escalation_cause=m.escalation_cause,
        urgency=m.urgency,
        sentiment=m.sentiment,
        response_time_ms=m.response_time_ms,
        ticket_id=t.id if t else None,
        category=t.category if t else None,
        priority=t.priority if t else None,
        ticket_status=t.status if t else None,
    )


# ── Human Handoff ─────────────────────────────────────────────────────────────

class HandoffRequest(BaseModel):
    mode: str  # "ai" | "human"


class HandoffResponse(BaseModel):
    conversation_id: str
    handoff_mode: str
    updated: bool


class AdminMessageRequest(BaseModel):
    content: str


@router.patch(
    "/conversations/{conversation_id}/handoff",
    response_model=HandoffResponse,
    summary="Toggle human/AI handoff mode (admin)",
)
async def set_handoff_mode(
    conversation_id: str,
    body: HandoffRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> HandoffResponse:
    """Set handoff_mode to 'ai' or 'human' for a conversation.

    When 'human', the AI auto-reply is paused and the admin can reply
    directly via POST /admin/conversations/{id}/message.
    """
    if body.mode not in ("ai", "human"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="mode must be 'ai' or 'human'",
        )

    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_with_messages(conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    await conv_repo.update(conversation_id, {"handoff_mode": body.mode})

    event_type = (
        event_logger.HANDOFF_STARTED if body.mode == "human" else event_logger.HANDOFF_ENDED
    )
    await event_logger.log(
        db,
        event_type,
        user_id=admin.id,
        conversation_id=conversation_id,
        details={"mode": body.mode, "admin_id": admin.id},
    )

    return HandoffResponse(conversation_id=conversation_id, handoff_mode=body.mode, updated=True)


@router.post(
    "/conversations/{conversation_id}/message",
    summary="Send an admin (agent) reply to a conversation (admin)",
)
async def admin_send_message(
    conversation_id: str,
    body: AdminMessageRequest,
    admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Post a message as sender_type='agent' on behalf of an admin.

    Used when handoff_mode='human' so the admin can reply directly without
    triggering the AI agent.
    """
    from app.repositories.message import MessageRepository

    conv_repo = ConversationRepository(db)
    conv = await conv_repo.get_with_messages(conversation_id)
    if conv is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    msg_repo = MessageRepository(db)
    agent_msg = await msg_repo.create_message(
        conversation_id=conversation_id,
        sender_type="agent",
        content=body.content.strip(),
    )

    await event_logger.log(
        db,
        event_logger.MESSAGE_RECEIVED,
        user_id=admin.id,
        conversation_id=conversation_id,
        channel=getattr(conv, "channel", "web"),
        details={"sender": "admin", "admin_id": admin.id},
    )

    from app.schemas.message import MessageResponse
    return MessageResponse.model_validate(agent_msg).model_dump()


# ── Support Queue ─────────────────────────────────────────────────────────────

class QueueItem(BaseModel):
    """One row in the admin support queue — conversation enriched with ticket + AI data."""
    conversation_id: str
    subject: Optional[str] = None
    user_id: str
    channel: str
    status: str
    handoff_mode: str
    created_at: datetime
    updated_at: datetime
    # From latest ticket linked to this conversation
    ticket_id: Optional[str] = None
    ticket_priority: Optional[str] = None
    ticket_status: Optional[str] = None
    ticket_category: Optional[str] = None
    # From latest agent_metrics row
    routed_agent: Optional[str] = None
    urgency: Optional[str] = None
    sentiment: Optional[str] = None


@router.get(
    "/queue",
    response_model=List[QueueItem],
    summary="Support queue — all active/escalated conversations enriched with ticket+AI data (admin)",
)
async def get_support_queue(
    _admin=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> List[QueueItem]:
    """Return all non-closed conversations enriched with the latest ticket and AI metrics.

    Covers escalated conversations, human-active handoffs, and any active conversation
    that has an open ticket — everything an on-call agent needs to triage.

    The response is ordered by updated_at descending (most recently active first).
    Ticket and AI data are fetched in two batch queries (no N+1).
    """
    from app.models.conversation import Conversation
    from app.models.ticket import Ticket
    from app.models.agent_metrics import AgentMetrics

    # 1. All non-closed conversations
    conv_result = await db.execute(
        select(Conversation)
        .where(Conversation.status != "closed")
        .order_by(Conversation.updated_at.desc())
        .limit(200)
    )
    conversations = list(conv_result.scalars().all())
    if not conversations:
        return []

    conv_ids = [c.id for c in conversations]

    # 2. Latest ticket per conversation (one batch query using row_number)
    # Sub-select ranks tickets per conversation by created_at desc
    ticket_rank_sub = (
        select(
            Ticket,
            func.row_number()
            .over(
                partition_by=Ticket.conversation_id,
                order_by=Ticket.created_at.desc(),
            )
            .label("rn"),
        )
        .where(Ticket.conversation_id.in_(conv_ids))
        .subquery()
    )
    ticket_result = await db.execute(
        select(ticket_rank_sub).where(ticket_rank_sub.c.rn == 1)
    )
    ticket_rows = ticket_result.mappings().all()
    ticket_map: dict = {row["conversation_id"]: row for row in ticket_rows}

    # 3. Latest agent_metrics per conversation (same pattern)
    metrics_rank_sub = (
        select(
            AgentMetrics,
            func.row_number()
            .over(
                partition_by=AgentMetrics.conversation_id,
                order_by=AgentMetrics.created_at.desc(),
            )
            .label("rn"),
        )
        .where(AgentMetrics.conversation_id.in_(conv_ids))
        .subquery()
    )
    metrics_result = await db.execute(
        select(metrics_rank_sub).where(metrics_rank_sub.c.rn == 1)
    )
    metrics_rows = metrics_result.mappings().all()
    metrics_map: dict = {row["conversation_id"]: row for row in metrics_rows}

    # 4. Assemble QueueItems
    items: List[QueueItem] = []
    for conv in conversations:
        t = ticket_map.get(conv.id)
        m = metrics_map.get(conv.id)
        items.append(QueueItem(
            conversation_id=conv.id,
            subject=conv.subject,
            user_id=conv.user_id,
            channel=conv.channel,
            status=conv.status,
            handoff_mode=getattr(conv, "handoff_mode", "ai") or "ai",
            created_at=conv.created_at,
            updated_at=conv.updated_at,
            ticket_id=t["id"] if t else None,
            ticket_priority=t["priority"] if t else None,
            ticket_status=t["status"] if t else None,
            ticket_category=t["category"] if t else None,
            routed_agent=m["routed_agent"] if m else None,
            urgency=m["urgency"] if m else None,
            sentiment=m["sentiment"] if m else None,
        ))
    return items
