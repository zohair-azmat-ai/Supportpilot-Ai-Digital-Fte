"""Conversation routes."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.repositories.conversation import ConversationRepository
from app.schemas.conversation import (
    ConversationDetailResponse,
    ConversationResponse,
    CreateConversationRequest,
)
from app.schemas.message import MessageResponse
from app.services.conversation import conversation_service

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get(
    "",
    response_model=List[ConversationResponse],
    summary="List conversations for the current user",
)
async def list_conversations(
    skip: int = 0,
    limit: int = 50,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> List[ConversationResponse]:
    """Return all conversations belonging to the authenticated user.

    Admins receive all conversations in the system.
    """
    if current_user.role == "admin":
        repo = ConversationRepository(db)
        convs = await repo.get_all_paginated(skip=skip, limit=limit)
    else:
        convs = await conversation_service.get_user_conversations(
            db, current_user.id, skip=skip, limit=limit
        )
    return [ConversationResponse.model_validate(c) for c in convs]


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new conversation",
)
async def create_conversation(
    data: CreateConversationRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationResponse:
    """Create a new conversation for the current user."""
    conv = await conversation_service.create_conversation(
        db,
        user_id=current_user.id,
        channel=data.channel,
        subject=data.subject,
    )
    return ConversationResponse.model_validate(conv)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get a conversation with its messages",
)
async def get_conversation(
    conversation_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationDetailResponse:
    """Retrieve a conversation and its full message history."""
    conv = await conversation_service.get_conversation_detail(
        db, conversation_id, current_user
    )
    messages = [MessageResponse.model_validate(m) for m in (conv.messages or [])]
    detail = ConversationDetailResponse.model_validate(conv)
    detail.messages = messages
    return detail


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Close / delete a conversation",
)
async def delete_conversation(
    conversation_id: str,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Close the specified conversation (sets status to 'closed')."""
    await conversation_service.close_conversation(db, conversation_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
