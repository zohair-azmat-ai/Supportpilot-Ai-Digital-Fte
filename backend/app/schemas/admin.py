"""Admin-specific Pydantic schemas."""

from __future__ import annotations

from pydantic import BaseModel


class AdminStatsResponse(BaseModel):
    """Aggregated platform statistics for the admin dashboard."""

    total_users: int
    total_tickets: int
    open_tickets: int
    total_conversations: int
    active_conversations: int
    resolved_today: int
