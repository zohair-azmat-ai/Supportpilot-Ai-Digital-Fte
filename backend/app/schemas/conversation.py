"""Conversation-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.message import MessageResponse


class CreateConversationRequest(BaseModel):
    """Request body for creating a new conversation."""

    channel: str = Field(
        default="web",
        description="Communication channel: web, email, or whatsapp",
        pattern="^(web|email|whatsapp)$",
    )
    subject: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional conversation subject/topic",
    )


class ConversationResponse(BaseModel):
    """Public representation of a conversation (without messages)."""

    id: str
    user_id: str
    channel: str
    status: str
    subject: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(ConversationResponse):
    """Conversation representation that includes full message history."""

    messages: List[MessageResponse] = Field(default_factory=list)
