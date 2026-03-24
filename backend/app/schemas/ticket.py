"""Ticket-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class CreateTicketRequest(BaseModel):
    """Request body for creating a support ticket."""

    title: str = Field(..., min_length=1, max_length=500, description="Ticket title")
    description: str = Field(..., min_length=1, description="Detailed ticket description")
    category: str = Field(
        default="general",
        description="Category: technical, billing, general, feature_request, bug",
    )
    priority: str = Field(
        default="medium",
        description="Priority level: low, medium, high, urgent",
        pattern="^(low|medium|high|urgent)$",
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Optional linked conversation ID",
    )


class UpdateTicketRequest(BaseModel):
    """Request body for partially updating a ticket."""

    title: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    priority: Optional[str] = Field(
        default=None,
        pattern="^(low|medium|high|urgent)$",
    )
    status: Optional[str] = Field(
        default=None,
        pattern="^(open|in_progress|resolved|closed)$",
    )
    assigned_to: Optional[str] = Field(
        default=None,
        description="UUID of the admin user to assign this ticket to",
    )


class TicketResponse(BaseModel):
    """Public representation of a ticket."""

    id: str
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    title: str
    description: str
    category: str
    priority: str
    status: str
    sentiment: Optional[str] = None
    urgency: Optional[str] = None
    escalation_reason: Optional[str] = None
    assigned_to: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TicketListResponse(BaseModel):
    """Paginated list of tickets."""

    items: List[TicketResponse]
    total: int
