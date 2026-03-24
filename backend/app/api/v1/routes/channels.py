"""
Channel webhook routes.

Inbound webhook endpoints for external channel integrations:
  POST /channels/whatsapp/inbound  — Twilio WhatsApp webhook
  POST /channels/email/inbound     — Gmail Pub/Sub push notification

Both routes:
  1. Parse the inbound payload via the appropriate channel adapter.
  2. Resolve or create the customer identity (cross-channel).
  3. Create/resume a conversation.
  4. Run the AI agent pipeline (inline for demo; Kafka in production).
  5. Send the AI reply back via the originating channel adapter.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.email import email_adapter
from app.channels.whatsapp import whatsapp_adapter, validate_twilio_signature
from app.core.config import settings
from app.core.database import get_db
from app.services.channel_identity import channel_identity_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["Channels"])


# ---------------------------------------------------------------------------
# WhatsApp / Twilio webhook
# ---------------------------------------------------------------------------


@router.post(
    "/whatsapp/inbound",
    summary="Twilio WhatsApp inbound webhook",
    response_class=Response,
    status_code=200,
)
async def whatsapp_inbound(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_twilio_signature: str = Header(default="", alias="X-Twilio-Signature"),
) -> Response:
    """
    Receive and process an inbound WhatsApp message from Twilio.

    Twilio sends form-encoded POST data. This endpoint:
    1. Validates the Twilio HMAC-SHA1 signature (if TWILIO_ENABLED).
    2. Parses the payload into an InboundMessage.
    3. Resolves the sender's customer identity.
    4. Runs the AI support pipeline.
    5. Sends the AI reply back via WhatsApp.
    6. Returns TwiML 200 OK (Twilio requires a 200 response).
    """
    if not settings.TWILIO_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp integration is not enabled",
        )

    # Parse form-encoded body
    form_data = await request.form()
    payload: dict[str, Any] = dict(form_data)

    # Validate Twilio signature in production
    if settings.ENVIRONMENT == "production":
        url = str(request.url)
        if not validate_twilio_signature(
            settings.TWILIO_AUTH_TOKEN, url, payload, x_twilio_signature
        ):
            logger.warning("Twilio webhook signature validation failed | url=%s", url)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature",
            )

    try:
        # 1. Parse inbound message
        inbound = await whatsapp_adapter.parse_inbound(payload)

        # 2. Resolve customer identity
        user = await channel_identity_service.resolve_or_create(
            db=db,
            channel="whatsapp",
            identifier_value=payload.get("sender_phone", inbound.sender_email.split("@")[0]),
            display_name=inbound.sender_name,
        )

        # 3. Run AI pipeline and reply
        ai_response_text = await _run_support_pipeline(
            db=db,
            user=user,
            inbound=inbound,
            channel="whatsapp",
        )

        # 4. Send WhatsApp reply
        phone = payload.get("sender_phone") or inbound.raw_payload.get("sender_phone", "")
        if phone and ai_response_text:
            await whatsapp_adapter.send_response(phone, ai_response_text)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("WhatsApp inbound processing failed: %s", exc, exc_info=True)
        # Always return 200 to Twilio — otherwise Twilio will retry repeatedly
        return Response(content="", status_code=200)

    # Return empty TwiML 200 — Twilio requires 200
    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
        status_code=200,
    )


# ---------------------------------------------------------------------------
# Gmail Pub/Sub webhook
# ---------------------------------------------------------------------------


@router.post(
    "/email/inbound",
    summary="Gmail Pub/Sub push notification webhook",
    response_class=Response,
    status_code=204,
)
async def email_inbound(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Receive and process a Gmail Pub/Sub push notification.

    Gmail sends a JSON body containing a base64-encoded notification with
    the emailAddress and historyId. This endpoint:
    1. Parses the notification to find the new Gmail message.
    2. Fetches the full message from Gmail API.
    3. Resolves the sender's customer identity.
    4. Runs the AI support pipeline.
    5. Sends the reply via Gmail API (same thread).
    6. Returns 204 (acknowledges the Pub/Sub push).
    """
    if not settings.GMAIL_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Gmail integration is not enabled",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON payload",
        )

    try:
        # 1. Parse inbound message
        inbound = await email_adapter.parse_inbound(payload)

        # 2. Resolve customer identity
        user = await channel_identity_service.resolve_or_create(
            db=db,
            channel="email",
            identifier_value=inbound.sender_email,
            display_name=inbound.sender_name,
        )

        # 3. Run AI pipeline
        ai_response_text = await _run_support_pipeline(
            db=db,
            user=user,
            inbound=inbound,
            channel="email",
        )

        # 4. Send email reply in same thread
        if ai_response_text:
            thread_id = inbound.raw_payload.get("thread_id")
            await email_adapter.send_response(
                recipient=inbound.sender_email,
                message=ai_response_text,
                thread_id=thread_id,
                subject=inbound.subject,
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Gmail inbound processing failed: %s", exc, exc_info=True)
        # Return 204 to acknowledge Pub/Sub (avoid redelivery loop)
        return Response(status_code=204)

    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Shared AI support pipeline
# ---------------------------------------------------------------------------


async def _run_support_pipeline(
    db: AsyncSession,
    user: Any,
    inbound: Any,
    channel: str,
) -> str:
    """
    Run the full AI support pipeline for an inbound channel message.

    Conversation lookup strategy (in order):
      1. If inbound.thread_id is set — resume conversation by thread_id.
         Handles email thread continuity (same Gmail threadId) and WhatsApp
         session continuity (same sender phone).
      2. Fallback — find the most recent active conversation for user+channel.
      3. If none found — create a new conversation.

    After the AI runs, stores all AI signals (sentiment, urgency, escalate),
    records full analytics metrics, logs platform events, and returns the
    AI response text.
    """
    from app.ai.agent import support_agent
    from app.repositories.conversation import ConversationRepository
    from app.repositories.message import MessageRepository
    from app.repositories.agent_metrics import AgentMetricsRepository
    from app.services.event_logger import event_logger

    conv_repo = ConversationRepository(db)
    msg_repo = MessageRepository(db)

    # ------------------------------------------------------------------
    # 1. Find or create conversation
    # ------------------------------------------------------------------

    active_conv = None

    # Priority: resume by thread_id (email thread / WhatsApp session)
    if inbound.thread_id:
        active_conv = await conv_repo.get_by_thread_id(inbound.thread_id)
        if active_conv:
            logger.info(
                "Resumed conversation by thread_id | channel=%s conv_id=%s thread_id=%s",
                channel,
                active_conv.id,
                inbound.thread_id,
            )

    # Fallback: most recent active conversation for this user+channel
    if active_conv is None:
        active_conv = await conv_repo.get_active_by_user_channel(user.id, channel)

    # Last resort: create a new conversation
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

    # ------------------------------------------------------------------
    # 2. Store inbound user message with channel metadata
    # ------------------------------------------------------------------

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

    # Log: message received
    await event_logger.log(
        db,
        event_logger.MESSAGE_RECEIVED,
        user_id=user.id,
        conversation_id=active_conv.id,
        channel=channel,
        details=user_msg_metadata,
    )

    # ------------------------------------------------------------------
    # 3. Build history and run agent
    # ------------------------------------------------------------------

    conv_with_msgs = await conv_repo.get_with_messages(active_conv.id)
    history = [
        {"sender_type": m.sender_type, "content": m.content}
        for m in (conv_with_msgs.messages if conv_with_msgs else [])
    ]

    t0 = time.monotonic()
    ai_result = await support_agent.run(
        db=db,
        user_id=user.id,
        conversation_id=active_conv.id,
        user_message=inbound.body,
        conversation_history=history,
    )
    response_ms = (time.monotonic() - t0) * 1000

    # ------------------------------------------------------------------
    # 4. Store AI reply with full AI signals
    # ------------------------------------------------------------------

    ai_msg_metadata: dict[str, Any] = {
        "channel": channel,
        "should_escalate": ai_result.should_escalate,
        "escalation_reason": ai_result.escalation_reason,
    }

    await msg_repo.create_message(
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

    # Log: AI response generated
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

    # ------------------------------------------------------------------
    # 5. Handle escalation
    # ------------------------------------------------------------------

    if ai_result.should_escalate:
        await conv_repo.update(active_conv.id, {"status": "escalated"})
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

    # ------------------------------------------------------------------
    # 6. Record full agent metrics (fire-and-forget)
    # ------------------------------------------------------------------

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

    return ai_result.response
