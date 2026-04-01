"""Message service — sends messages through the tool-based AI agent."""

from __future__ import annotations

import time
import logging
from typing import Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import support_agent
from app.models.message import Message
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.services.event_logger import event_logger

logger = logging.getLogger(__name__)


class MessageService:
    """Handles sending messages and generating AI agent replies."""

    async def send_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        content: str,
        plan_tier: str = "free",
    ) -> Tuple[Message, Message]:
        """Store a user message, run the AI agent, and store the reply.

        The agent runs the full tool workflow:
          get_customer_history → search_knowledge_base → create_ticket
          → [escalate_to_human] → send_response

        Args:
            db: Active database session.
            conversation_id: Target conversation ID.
            user_id: ID of the sending user.
            content: User's message text.
            plan_tier: The user's current billing tier for limit enforcement.

        Returns:
            Tuple of (user_message, ai_message).

        Raises:
            HTTPException 404: Conversation not found.
            HTTPException 403: User does not own conversation.
        """
        conv_repo = ConversationRepository(db)
        conversation = await conv_repo.get_with_messages(conversation_id)

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found",
            )

        if conversation.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to post in this conversation",
            )

        msg_repo = MessageRepository(db)

        # 1. Persist user message
        user_message = await msg_repo.create_message(
            conversation_id=conversation_id,
            sender_type="user",
            content=content,
        )

        # Log: message received
        await event_logger.log(
            db,
            event_logger.MESSAGE_RECEIVED,
            user_id=user_id,
            conversation_id=conversation_id,
            channel=getattr(conversation, "channel", "web"),
        )

        # ── Billing enforcement ────────────────────────────────────────────────
        from app.billing.limits import check_limits
        from app.billing.usage_meter import usage_meter as _meter

        limit_result = await check_limits(
            user_id=user_id,
            plan_tier=plan_tier,
            action="message",
            db=db,
        )

        if limit_result.hard_blocked:
            logger.info(
                "[message_service:blocked] user=%s plan=%s messages=%d/%d",
                user_id, plan_tier, limit_result.current_count, limit_result.limit,
            )
            blocked_msg = await msg_repo.create_message(
                conversation_id=conversation_id,
                sender_type="ai",
                content=limit_result.message,
                intent="billing_limit",
            )
            return user_message, blocked_msg

        # Record usage now that the request will be processed
        await _meter.record_message(user_id)

        # 2. Build conversation history (messages before this one)
        history = [
            {"sender_type": m.sender_type, "content": m.content}
            for m in (conversation.messages or [])
        ]

        # 3. Run tool-based AI agent
        t0 = time.monotonic()
        ai_result = await support_agent.run(
            db=db,
            user_id=user_id,
            conversation_id=conversation_id,
            user_message=content,
            conversation_history=history,
        )
        response_ms = (time.monotonic() - t0) * 1000

        # Soft-limit warning: append a note to the AI response
        response_text = ai_result.response
        if limit_result.soft_warning:
            response_text = (
                f"{response_text}\n\n"
                f"---\n"
                f"_Note: {limit_result.message}_"
            )

        # 4. Persist AI response with full AI signals
        ai_message = await msg_repo.create_message(
            conversation_id=conversation_id,
            sender_type="ai",
            content=response_text,
            intent=ai_result.intent,
            ai_confidence=ai_result.confidence,
            sentiment=getattr(ai_result, "sentiment", None),
            urgency=getattr(ai_result, "urgency", None),
            escalate=ai_result.should_escalate,
        )

        # Log: AI response generated
        await event_logger.log(
            db,
            event_logger.AI_RESPONSE_GENERATED,
            user_id=user_id,
            conversation_id=conversation_id,
            channel=getattr(conversation, "channel", "web"),
            intent=ai_result.intent,
            sentiment=getattr(ai_result, "sentiment", None),
            urgency=getattr(ai_result, "urgency", None),
            confidence=ai_result.confidence,
            details={
                "escalated": ai_result.should_escalate,
                "tools_called": ai_result.tools_called,
            },
        )

        # 5. Escalate conversation if the agent flagged it
        if ai_result.should_escalate and conversation.status == "active":
            await conv_repo.update(conversation_id, {"status": "escalated"})
            await event_logger.log(
                db,
                event_logger.ISSUE_ESCALATED,
                user_id=user_id,
                conversation_id=conversation_id,
                channel=getattr(conversation, "channel", "web"),
                intent=ai_result.intent,
                details={
                    "escalation_reason": ai_result.escalation_reason,
                    "escalation_level": getattr(ai_result, "escalation_level", "none"),
                    "escalation_cause": getattr(ai_result, "escalation_cause", None),
                },
            )

        if getattr(ai_result, "similar_issue_detected", False):
            await event_logger.log(
                db,
                event_logger.SIMILAR_ISSUE_DETECTED,
                user_id=user_id,
                conversation_id=conversation_id,
                channel=getattr(conversation, "channel", "web"),
                details={"intent": ai_result.intent},
            )

        # 6. Record metrics (fire-and-forget — failure does not affect response)
        try:
            await self._record_metrics(
                db=db,
                conversation=conversation,
                user_id=user_id,
                ai_result=ai_result,
                response_ms=response_ms,
            )
        except Exception as exc:
            logger.warning("Failed to record agent metrics: %s", exc)

        return user_message, ai_message

    async def _record_metrics(
        self,
        db: AsyncSession,
        conversation: object,
        user_id: str,
        ai_result: object,
        response_ms: float,
    ) -> None:
        """Persist agent metrics for analytics."""
        from app.core.config import settings
        from app.repositories.agent_metrics import AgentMetricsRepository

        metrics_repo = AgentMetricsRepository(db)
        await metrics_repo.record({
            "conversation_id": conversation.id,  # type: ignore[attr-defined]
            "user_id": user_id,
            "channel": getattr(conversation, "channel", "web"),
            "intent_detected": ai_result.intent,  # type: ignore[attr-defined]
            "confidence_score": ai_result.confidence,  # type: ignore[attr-defined]
            "sentiment": getattr(ai_result, "sentiment", None),
            "urgency": getattr(ai_result, "urgency", None),
            "tools_called": getattr(ai_result, "tools_called", []),
            "iterations": getattr(ai_result, "iterations", 0),
            "response_time_ms": response_ms,
            "model_used": settings.OPENAI_MODEL,
            "was_escalated": ai_result.should_escalate,  # type: ignore[attr-defined]
            "escalation_reason": ai_result.escalation_reason,  # type: ignore[attr-defined]
            "escalation_level": getattr(ai_result, "escalation_level", "none"),
            "escalation_cause": getattr(ai_result, "escalation_cause", None),
            "similar_issue_detected": getattr(ai_result, "similar_issue_detected", False),
            "ticket_created": getattr(ai_result, "ticket_created", False),
            "kb_articles_found": getattr(ai_result, "kb_articles_found", 0),
        })


message_service = MessageService()
