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

logger = logging.getLogger(__name__)


class MessageService:
    """Handles sending messages and generating AI agent replies."""

    async def send_message(
        self,
        db: AsyncSession,
        conversation_id: str,
        user_id: str,
        content: str,
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

        # 4. Persist AI response
        ai_message = await msg_repo.create_message(
            conversation_id=conversation_id,
            sender_type="ai",
            content=ai_result.response,
            intent=ai_result.intent,
            ai_confidence=ai_result.confidence,
            metadata=(
                {
                    "should_escalate": ai_result.should_escalate,
                    "escalation_reason": ai_result.escalation_reason,
                }
                if ai_result.should_escalate
                else None
            ),
        )

        # 5. Escalate conversation if the agent flagged it
        if ai_result.should_escalate and conversation.status == "active":
            await conv_repo.update(conversation_id, {"status": "escalated"})

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
            "tools_called": getattr(ai_result, "tools_called", []),
            "iterations": getattr(ai_result, "iterations", 0),
            "response_time_ms": response_ms,
            "model_used": settings.OPENAI_MODEL,
            "was_escalated": ai_result.should_escalate,  # type: ignore[attr-defined]
            "escalation_reason": ai_result.escalation_reason,  # type: ignore[attr-defined]
            "ticket_created": getattr(ai_result, "ticket_created", False),
            "kb_articles_found": getattr(ai_result, "kb_articles_found", 0),
        })


message_service = MessageService()
