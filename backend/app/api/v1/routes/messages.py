"""Message routes."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_active_user, get_db
from app.schemas.message import MessagePairResponse, MessageResponse, SendMessageRequest
from app.services.message import message_service

logger = logging.getLogger(__name__)

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
        plan_tier=getattr(current_user, "plan_tier", "free") or "free",
    )
    return MessagePairResponse(
        user_message=MessageResponse.model_validate(user_msg),
        ai_message=MessageResponse.model_validate(ai_msg),
    )


@router.post(
    "/conversations/{conversation_id}/messages/stream",
    summary="Send a message and receive a streaming AI reply (SSE)",
)
async def stream_message(
    conversation_id: str,
    data: SendMessageRequest,
    current_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Post a message and receive the AI reply as a stream of Server-Sent Events.

    Event types:
      - ``user_message``  — the stored user message (fires immediately after DB write)
      - ``token``         — one chunk of the AI reply text
      - ``done``          — the complete AI message object (streaming finished)
      - ``error``         — error detail string (streaming failed)

    The ``done`` event is always sent, even on partial failure, so the client
    can fall back to the full response if needed.
    """

    async def event_stream() -> AsyncGenerator[str, None]:
        def _sse(payload: dict) -> str:
            return f"data: {json.dumps(payload, default=str)}\n\n"

        try:
            # Run the full agent pipeline (context → decision → tool loop → save)
            user_msg, ai_msg = await message_service.send_message(
                db,
                conversation_id=conversation_id,
                user_id=current_user.id,
                content=data.content,
                plan_tier=getattr(current_user, "plan_tier", "free") or "free",
            )

            # Confirm the stored user message to the client
            yield _sse({
                "type": "user_message",
                "message": MessageResponse.model_validate(user_msg).model_dump(mode="json"),
            })

            # Stream the AI reply word-by-word with a capped total duration of ~3 s
            reply_text: str = ai_msg.content
            words = reply_text.split(" ")
            delay = min(0.04, 3.0 / max(len(words), 1))

            for i, word in enumerate(words):
                chunk = word if i == 0 else f" {word}"
                yield _sse({"type": "token", "content": chunk})
                await asyncio.sleep(delay)

            # Final event — complete AI message with all metadata
            yield _sse({
                "type": "done",
                "message": MessageResponse.model_validate(ai_msg).model_dump(mode="json"),
            })

        except Exception:
            logger.exception("stream_message: pipeline error for conv=%s", conversation_id)
            yield _sse({"type": "error", "message": "Failed to process message. Please try again."})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
