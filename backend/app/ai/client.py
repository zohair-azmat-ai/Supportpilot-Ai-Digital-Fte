"""OpenAI async client singleton."""

from __future__ import annotations

from typing import Optional

from openai import AsyncOpenAI

from app.core.config import settings

_client: Optional[AsyncOpenAI] = None


def get_openai_client() -> AsyncOpenAI:
    """Return a shared AsyncOpenAI client instance (lazy initialisation).

    The client is created once and reused for all subsequent calls, taking
    advantage of connection pooling within the openai library.
    """
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client
