"""Authentication-related Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    """Request body for user registration."""

    name: str = Field(..., min_length=1, max_length=255, description="Full name")
    email: EmailStr = Field(..., description="Unique email address")
    password: str = Field(
        ...,
        min_length=8,
        max_length=72,
        description="Password (8–72 characters). bcrypt's hard limit is 72 bytes.",
    )
    role: Optional[str] = Field(
        default="customer",
        description="User role: 'customer' or 'admin'",
        pattern="^(customer|admin)$",
    )


class LoginRequest(BaseModel):
    """Request body for user login."""

    email: EmailStr = Field(..., description="Registered email address")
    password: str = Field(..., description="Account password")


class UserResponse(BaseModel):
    """Public representation of a user."""

    id: str
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Response returned on successful authentication."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
