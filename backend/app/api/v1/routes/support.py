"""Public support form route."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.schemas.support import SupportFormRequest, SupportSubmitResponse
from app.services.support import support_service

router = APIRouter(prefix="/support", tags=["Support"])


@router.post(
    "/submit",
    response_model=SupportSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a public support request",
)
async def submit_support_form(
    data: SupportFormRequest,
    db: AsyncSession = Depends(get_db),
) -> SupportSubmitResponse:
    """Process a support form submission.

    This endpoint is publicly accessible (no authentication required).
    It creates or finds a user account, opens a conversation, generates an
    AI response, and creates a linked support ticket.
    """
    return await support_service.submit_support_form(db, data)
