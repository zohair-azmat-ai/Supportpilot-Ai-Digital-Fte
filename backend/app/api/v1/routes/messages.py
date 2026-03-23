"""Message routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.schemas.message import MessagePairResponse, MessageResponse, SendMessageRequest
from app.services.message import message_service

router = APIRouter(tags=["Messages"])


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessagePairResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Send a message and receive an AI reply",
)
async def send_message(
    conversation_id: str,
    data: SendMessageRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> MessagePairResponse:
    """Post a message to a conversation and receive the AI-generated reply."""
    user_msg, ai_msg = await message_service.send_message(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        content=data.content,
    )
    return MessagePairResponse(
        user_message=MessageResponse.model_validate(user_msg),
        ai_message=MessageResponse.model_validate(ai_msg),
    )
