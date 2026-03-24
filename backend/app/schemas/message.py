"""Message-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    """Request body for sending a message in a conversation."""

    content: str = Field(..., min_length=1, description="Message content (non-empty)")


class MessageResponse(BaseModel):
    """Public representation of a single message."""

    id: str
    conversation_id: str
    sender_type: str
    content: str
    intent: Optional[str] = None
    ai_confidence: Optional[float] = None
    sentiment: Optional[str] = None
    urgency: Optional[str] = None
    escalate: Optional[bool] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessagePairResponse(BaseModel):
    """Pair of the user's message and the AI reply."""

    user_message: MessageResponse
    ai_message: MessageResponse
