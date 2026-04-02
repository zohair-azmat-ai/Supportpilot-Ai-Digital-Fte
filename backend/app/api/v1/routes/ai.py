"""AI utility endpoints — lightweight, stateless helpers."""

from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.client import get_openai_client
from app.core.config import settings
from app.core.deps import get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI"])


class SuggestionsRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)


class SuggestionsResponse(BaseModel):
    suggestions: list[str]


def _parse_suggestions(text: str, max_count: int = 3) -> list[str]:
    """Extract clean suggestion strings from the model's raw output.

    Strips leading list markers (1. / - / * / •) and blank lines, then
    returns up to *max_count* non-empty strings.
    """
    lines = text.strip().splitlines()
    cleaned: list[str] = []
    for line in lines:
        line = re.sub(r"^[\s\d]+[.)]\s*", "", line)   # "1. " / "2) "
        line = re.sub(r"^[-*•]\s*", "", line)          # "- " / "* " / "• "
        line = line.strip().strip('"').strip("'")
        if line:
            cleaned.append(line)
        if len(cleaned) == max_count:
            break
    return cleaned


@router.post(
    "/suggestions",
    response_model=SuggestionsResponse,
    summary="Generate 2–3 short smart reply suggestions for a user message",
)
async def get_suggestions(
    data: SuggestionsRequest,
    _current_user=Depends(get_current_active_user),
) -> SuggestionsResponse:
    """Return up to 3 short one-line customer support reply suggestions.

    Uses the same shared OpenAI client and model as the rest of the pipeline.
    No DB access, no tool calls — single completion call only.
    """
    prompt = (
        "You are a customer support assistant. "
        "Generate exactly 3 short, helpful reply suggestions for the following customer message. "
        "Each suggestion must be one sentence, on its own line, with no numbering, no markdown, "
        "no bullet points, and no extra commentary.\n\n"
        f"Customer message: {data.message}"
    )

    try:
        client = get_openai_client()
        completion = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=120,
            temperature=0.7,
        )
        raw = (completion.choices[0].message.content or "").strip()
    except Exception:
        logger.exception("get_suggestions: OpenAI call failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate suggestions. Please try again.",
        )

    suggestions = _parse_suggestions(raw)

    if not suggestions:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Model returned an empty response.",
        )

    return SuggestionsResponse(suggestions=suggestions)
