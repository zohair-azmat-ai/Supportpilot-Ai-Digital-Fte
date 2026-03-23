"""
KnowledgeBase model — support articles and documentation.

Stores support articles, FAQs, and troubleshooting guides.
The `embedding` JSON field is reserved for pgvector integration in Phase 2.
Simple keyword search is used until vector search is enabled.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeBase(Base):
    """Support article or FAQ entry in the knowledge base."""

    __tablename__ = "knowledge_base"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        # Examples: 'billing', 'technical', 'general'
    )
    tags: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        # Comma-separated list of keywords used for simple search before vector search is enabled
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    embedding: Mapped[Optional[list]] = mapped_column(
        JSON,
        nullable=True,
        # Reserved for Phase 2 pgvector integration — store as a list of floats
    )
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    def to_search_string(self) -> str:
        """Return a combined string of searchable fields for full-text matching.

        Combines the article title, full content body, and tag keywords into a
        single lowercase string. Used for in-process keyword matching until a
        dedicated full-text or vector search backend is available.
        """
        parts = [self.title or "", self.content or "", self.tags or ""]
        return " ".join(parts).lower()

    def __repr__(self) -> str:
        return (
            f"<KnowledgeBase id={self.id} title={self.title!r} "
            f"category={self.category} active={self.is_active}>"
        )
