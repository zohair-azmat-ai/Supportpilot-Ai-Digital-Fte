"""BillingEvent SQLAlchemy model — audit log for plan/subscription changes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class BillingEvent(Base):
    """One row per billing lifecycle event (plan change, checkout attempt, etc.)."""

    __tablename__ = "billing_events"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Event type — controlled vocabulary:
    #   plan_activated   — first plan assigned to user
    #   plan_changed     — plan_tier updated (dev/demo path)
    #   trial_started    — subscription_status → trial
    #   checkout_requested — stub POST /checkout-session called
    #   subscription_activated  — Stripe webhook (future)
    #   subscription_canceled   — Stripe webhook (future)
    #   payment_failed          — Stripe webhook (future)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)

    old_tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    new_tier: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Snapshot of subscription_status at the time of this event
    subscription_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Free-form payload for extra context (Stripe session IDs, amounts, etc.)
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], lazy="select")  # noqa: F821

    def __repr__(self) -> str:
        return f"<BillingEvent id={self.id} type={self.event_type} user={self.user_id}>"
