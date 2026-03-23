"""
Gmail Poller Worker — polls Gmail for new support emails and runs the AI pipeline.

This worker runs as a separate asyncio task alongside the main application (or
as a standalone process). It periodically fetches unread emails from the Gmail
INBOX, processes each through the full AI support pipeline, sends a reply, and
marks the email as read.

Activation
----------
Set GMAIL_ENABLED=true and configure Gmail credentials in backend/.env.
The worker is started automatically on app startup if GMAIL_ENABLED=true.

Polling vs. Pub/Sub
-------------------
- Polling (this file): simpler, no Google Cloud Pub/Sub setup required.
  Suitable for demo and low-volume use.
- Pub/Sub webhooks (channels.py → POST /channels/email/inbound): lower latency,
  no polling overhead. Recommended for production.

Set GMAIL_POLL_INTERVAL_SECONDS to control frequency (default: 30s).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.email import email_adapter
from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


class GmailPollerWorker:
    """Periodically polls Gmail for unread support emails and triggers the AI pipeline."""

    def __init__(self) -> None:
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self.processed_count = 0
        self.error_count = 0

    async def start(self) -> None:
        """Start the polling loop as a background task."""
        if not settings.GMAIL_ENABLED:
            logger.info("GmailPollerWorker: GMAIL_ENABLED=false — not starting")
            return

        logger.info(
            "GmailPollerWorker starting | interval=%ds",
            settings.GMAIL_POLL_INTERVAL_SECONDS,
        )
        self._running = True
        self._task = asyncio.create_task(self._poll_loop(), name="gmail-poller")

    async def stop(self) -> None:
        """Gracefully stop the polling loop."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info(
            "GmailPollerWorker stopped | processed=%d errors=%d",
            self.processed_count,
            self.error_count,
        )

    async def _poll_loop(self) -> None:
        """Main polling loop — runs until self._running is False."""
        while self._running:
            try:
                await self._poll_once()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("GmailPollerWorker._poll_loop error: %s", exc, exc_info=True)
                self.error_count += 1

            # Wait before next poll
            try:
                await asyncio.sleep(settings.GMAIL_POLL_INTERVAL_SECONDS)
            except asyncio.CancelledError:
                break

    async def _poll_once(self) -> None:
        """Fetch unread emails and process each one."""
        # Gmail API is synchronous — run in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        messages = await loop.run_in_executor(
            None, email_adapter.fetch_unread_messages
        )

        if not messages:
            logger.debug("GmailPollerWorker: no new messages")
            return

        logger.info("GmailPollerWorker: found %d unread message(s)", len(messages))

        for raw_msg in messages:
            msg_id = raw_msg.get("id")
            try:
                await self._process_one(raw_msg)
                self.processed_count += 1
                # Mark as read in thread pool
                if msg_id:
                    await loop.run_in_executor(
                        None, email_adapter.mark_as_read, msg_id
                    )
            except Exception as exc:
                logger.error(
                    "GmailPollerWorker failed to process message %s: %s", msg_id, exc
                )
                self.error_count += 1

    async def _process_one(self, raw_msg: dict) -> None:
        """Process a single Gmail message through the AI support pipeline."""
        # Parse message (synchronous method, fast enough to run inline)
        inbound = email_adapter.parse_gmail_message_object(raw_msg)
        if inbound is None:
            # Skipped (e.g., sent by us, or parse error)
            return

        logger.info(
            "Processing email | from=%s subject=%s",
            inbound.sender_email,
            inbound.subject,
        )

        # Open a DB session for this request
        async with AsyncSessionLocal() as db:
            try:
                await self._run_pipeline(db, inbound, raw_msg)
                await db.commit()
            except Exception as exc:
                await db.rollback()
                raise exc

    async def _run_pipeline(self, db: AsyncSession, inbound: object, raw_msg: dict) -> None:
        """Resolve identity, run AI agent, and send email reply."""
        import time as _time

        from app.ai.agent import support_agent
        from app.repositories.agent_metrics import AgentMetricsRepository
        from app.repositories.conversation import ConversationRepository
        from app.repositories.message import MessageRepository
        from app.services.channel_identity import channel_identity_service

        # 1. Resolve/create customer
        user = await channel_identity_service.resolve_or_create(
            db=db,
            channel="email",
            identifier_value=inbound.sender_email,
            display_name=inbound.sender_name,
        )

        # 2. Find or create active email conversation
        conv_repo = ConversationRepository(db)
        thread_id: str | None = inbound.raw_payload.get("thread_id")

        # Try to reuse an active conversation with same thread_id (stored in subject)
        all_convs = await conv_repo.get_by_user(user.id, skip=0, limit=20)
        active_conv = None
        for c in all_convs:
            if c.channel == "email" and c.status == "active":
                active_conv = c
                break

        if active_conv is None:
            active_conv = await conv_repo.create({
                "user_id": user.id,
                "channel": "email",
                "subject": (inbound.subject or "")[:500],
                "status": "active",
            })

        # 3. Store user message
        msg_repo = MessageRepository(db)
        await msg_repo.create_message(
            conversation_id=active_conv.id,
            sender_type="user",
            content=inbound.body,
        )

        # 4. Build history
        conv_with_msgs = await conv_repo.get_with_messages(active_conv.id)
        history = [
            {"sender_type": m.sender_type, "content": m.content}
            for m in (conv_with_msgs.messages if conv_with_msgs else [])
        ]

        # 5. Run AI agent
        t0 = _time.monotonic()
        ai_result = await support_agent.run(
            db=db,
            user_id=user.id,
            conversation_id=active_conv.id,
            user_message=inbound.body,
            conversation_history=history,
        )
        response_ms = (_time.monotonic() - t0) * 1000

        # 6. Store AI reply
        await msg_repo.create_message(
            conversation_id=active_conv.id,
            sender_type="ai",
            content=ai_result.response,
            intent=ai_result.intent,
            ai_confidence=ai_result.confidence,
            metadata={"channel": "email", "thread_id": thread_id},
        )

        if ai_result.should_escalate:
            await conv_repo.update(active_conv.id, {"status": "escalated"})

        # 7. Send reply via Gmail
        await email_adapter.send_response(
            recipient=inbound.sender_email,
            message=ai_result.response,
            thread_id=thread_id,
            subject=inbound.subject,
        )

        # 8. Record metrics
        try:
            metrics_repo = AgentMetricsRepository(db)
            await metrics_repo.record({
                "conversation_id": active_conv.id,
                "user_id": user.id,
                "channel": "email",
                "intent_detected": ai_result.intent,
                "confidence_score": ai_result.confidence,
                "tools_called": ai_result.tools_called,
                "iterations": ai_result.iterations,
                "response_time_ms": response_ms,
                "model_used": settings.OPENAI_MODEL,
                "was_escalated": ai_result.should_escalate,
                "escalation_reason": ai_result.escalation_reason,
                "ticket_created": ai_result.ticket_created,
                "kb_articles_found": ai_result.kb_articles_found,
            })
        except Exception as exc:
            logger.warning("Failed to record email metrics: %s", exc)

        logger.info(
            "Email pipeline complete | user=%s intent=%s escalated=%s response_ms=%.0f",
            user.id,
            ai_result.intent,
            ai_result.should_escalate,
            response_ms,
        )


# Module-level singleton
gmail_poller = GmailPollerWorker()
