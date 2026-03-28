"""Shared inbound channel pipeline helpers."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ChannelPipelineResult:
    """Structured result from processing one inbound channel message."""

    conversation_id: str
    ai_message_id: str
    response_text: str
    user_id: str
    sender_phone: str | None = None
    intent: str | None = None
    confidence: float | None = None
    escalated: bool = False


async def run_inbound_support_pipeline(
    db: AsyncSession,
    user: Any,
    inbound: Any,
    channel: str,
) -> ChannelPipelineResult:
    """Run the shared AI support pipeline for an inbound channel message."""
    from app.ai.agent import support_agent
    from app.repositories.agent_metrics import AgentMetricsRepository
    from app.repositories.conversation import ConversationRepository
    from app.repositories.message import MessageRepository
    from app.services.event_logger import event_logger

    conv_repo = ConversationRepository(db)
    msg_repo = MessageRepository(db)

    active_conv = None
    if inbound.thread_id:
        active_conv = await conv_repo.get_by_thread_id_channel(inbound.thread_id, channel)
        if active_conv:
            logger.info(
                "Resumed conversation by thread_id | channel=%s conv_id=%s thread_id=%s",
                channel,
                active_conv.id,
                inbound.thread_id,
            )

    if active_conv is None:
        active_conv = await conv_repo.get_active_by_user_channel(user.id, channel)

    if active_conv is None:
        conv_data: dict[str, Any] = {
            "user_id": user.id,
            "channel": channel,
            "subject": inbound.subject[:500] if inbound.subject else None,
            "status": "active",
        }
        if inbound.thread_id:
            conv_data["thread_id"] = inbound.thread_id
        active_conv = await conv_repo.create(conv_data)
        logger.info(
            "Created new %s conversation | conv_id=%s user_id=%s thread_id=%s",
            channel,
            active_conv.id,
            user.id,
            inbound.thread_id,
        )

    user_msg_metadata: dict[str, Any] = {"channel": channel}
    if inbound.thread_id:
        user_msg_metadata["thread_id"] = inbound.thread_id
    if inbound.external_id:
        user_msg_metadata["external_id"] = inbound.external_id
    if inbound.sender_phone:
        user_msg_metadata["sender_phone"] = inbound.sender_phone

    await msg_repo.create_message(
        conversation_id=active_conv.id,
        sender_type="user",
        content=inbound.body,
        metadata=user_msg_metadata,
    )

    await event_logger.log(
        db,
        event_logger.MESSAGE_RECEIVED,
        user_id=user.id,
        conversation_id=active_conv.id,
        channel=channel,
        details=user_msg_metadata,
    )

    conv_with_msgs = await conv_repo.get_with_messages(active_conv.id)
    history = [
        {"sender_type": m.sender_type, "content": m.content}
        for m in (conv_with_msgs.messages if conv_with_msgs else [])
    ]

    logger.info(
        "[pipeline:triage] conversation_id=%s user_id=%s channel=%s turn=%d",
        active_conv.id, user.id, channel, len(history),
    )
    t0 = time.monotonic()
    ai_result = await support_agent.run(
        db=db,
        user_id=user.id,
        conversation_id=active_conv.id,
        user_message=inbound.body,
        conversation_history=history,
    )
    response_ms = (time.monotonic() - t0) * 1000
    logger.info(
        "[pipeline:response] conversation_id=%s intent=%s escalated=%s response_ms=%.0f",
        active_conv.id, ai_result.intent, ai_result.should_escalate, response_ms,
    )

    ai_msg_metadata: dict[str, Any] = {
        "channel": channel,
        "should_escalate": ai_result.should_escalate,
        "escalation_reason": ai_result.escalation_reason,
    }
    if inbound.thread_id:
        ai_msg_metadata["thread_id"] = inbound.thread_id
    if inbound.external_id:
        ai_msg_metadata["source_external_id"] = inbound.external_id
    if inbound.sender_phone:
        ai_msg_metadata["sender_phone"] = inbound.sender_phone

    ai_message = await msg_repo.create_message(
        conversation_id=active_conv.id,
        sender_type="ai",
        content=ai_result.response,
        intent=ai_result.intent,
        ai_confidence=ai_result.confidence,
        sentiment=getattr(ai_result, "sentiment", None),
        urgency=getattr(ai_result, "urgency", None),
        escalate=ai_result.should_escalate,
        metadata=ai_msg_metadata,
    )

    await event_logger.log(
        db,
        event_logger.AI_RESPONSE_GENERATED,
        user_id=user.id,
        conversation_id=active_conv.id,
        channel=channel,
        intent=ai_result.intent,
        sentiment=getattr(ai_result, "sentiment", None),
        urgency=getattr(ai_result, "urgency", None),
        confidence=ai_result.confidence,
        details={
            "escalated": ai_result.should_escalate,
            "tools_called": ai_result.tools_called,
        },
    )

    if ai_result.should_escalate:
        await conv_repo.update(active_conv.id, {"status": "escalated"})
        logger.info(
            "[pipeline:escalation] conversation_id=%s reason=%r level=%s cause=%s",
            active_conv.id,
            ai_result.escalation_reason,
            getattr(ai_result, "escalation_level", "none"),
            getattr(ai_result, "escalation_cause", None),
        )
        await event_logger.log(
            db,
            event_logger.ISSUE_ESCALATED,
            user_id=user.id,
            conversation_id=active_conv.id,
            channel=channel,
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
            user_id=user.id,
            conversation_id=active_conv.id,
            channel=channel,
            details={"intent": ai_result.intent},
        )

    try:
        metrics_repo = AgentMetricsRepository(db)
        await metrics_repo.record({
            "conversation_id": active_conv.id,
            "user_id": user.id,
            "channel": channel,
            "intent_detected": ai_result.intent,
            "confidence_score": ai_result.confidence,
            "sentiment": getattr(ai_result, "sentiment", None),
            "urgency": getattr(ai_result, "urgency", None),
            "tools_called": ai_result.tools_called,
            "iterations": ai_result.iterations,
            "response_time_ms": response_ms,
            "model_used": settings.OPENAI_MODEL,
            "was_escalated": ai_result.should_escalate,
            "escalation_reason": ai_result.escalation_reason,
            "escalation_level": getattr(ai_result, "escalation_level", "none"),
            "escalation_cause": getattr(ai_result, "escalation_cause", None),
            "similar_issue_detected": getattr(ai_result, "similar_issue_detected", False),
            "ticket_created": ai_result.ticket_created,
            "kb_articles_found": ai_result.kb_articles_found,
        })
    except Exception as exc:
        logger.warning("Failed to record channel metrics: %s", exc)

    logger.info(
        "AI pipeline complete | channel=%s user=%s conv=%s intent=%s escalated=%s response_ms=%.0f",
        channel,
        user.id,
        active_conv.id,
        ai_result.intent,
        ai_result.should_escalate,
        response_ms,
    )

    return ChannelPipelineResult(
        conversation_id=active_conv.id,
        ai_message_id=ai_message.id,
        response_text=ai_result.response,
        user_id=user.id,
        sender_phone=inbound.sender_phone,
        intent=ai_result.intent,
        confidence=ai_result.confidence,
        escalated=ai_result.should_escalate,
    )
