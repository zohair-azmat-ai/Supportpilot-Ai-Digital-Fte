"""Support form Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field


class SupportFormRequest(BaseModel):
    """Request body for the public support submission form."""

    name: str = Field(..., min_length=1, max_length=255, description="Submitter's name")
    email: EmailStr = Field(..., description="Contact email address")
    subject: str = Field(..., min_length=1, max_length=500, description="Issue subject")
    message: str = Field(..., min_length=1, description="Detailed message / issue description")
    category: str = Field(
        default="general",
        description="Issue category: technical, billing, general, feature_request, bug",
    )
    priority: str = Field(
        default="medium",
        description="Requested priority: low, medium, high, urgent",
        pattern="^(low|medium|high|urgent)$",
    )


class SupportSubmitResponse(BaseModel):
    """Response returned after a successful support form submission."""

    conversation_id: str
    ticket_id: str
    confirmation_message: str
    ai_response: str
