"""
Channel webhook routes.

Inbound webhook endpoints for external channel integrations:
  POST /channels/whatsapp/inbound  - Twilio WhatsApp webhook
  POST /channels/whatsapp/status   - Twilio delivery status callback
  POST /channels/email/inbound     - Gmail Pub/Sub push notification
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.channels.email import email_adapter
from app.channels.whatsapp import whatsapp_adapter, validate_twilio_signature
from app.core.config import settings
from app.core.database import get_db
from app.repositories.message import MessageRepository
from app.services.channel_identity import channel_identity_service
from app.services.channel_pipeline import run_inbound_support_pipeline
from app.services.event_logger import event_logger

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/channels", tags=["Channels"])


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
    """Receive and process an inbound WhatsApp message from Twilio."""
    # ------------------------------------------------------------------ #
    # DEBUG MODE — temporary patch to verify Twilio reaches this endpoint #
    # ------------------------------------------------------------------ #
    logger.info("=== WHATSAPP INBOUND HIT ===")
    logger.info("DEBUG | method=%s url=%s", request.method, str(request.url))
    logger.info("DEBUG | headers=%s", dict(request.headers))

    try:
        form_data = await request.form()
        payload: dict[str, Any] = dict(form_data)
    except Exception as exc:
        logger.error("DEBUG | failed to parse form body: %s", exc)
        payload = {}

    logger.info("DEBUG | raw form fields=%s", payload)
    logger.info(
        "DEBUG | Body=%r From=%r To=%r MessageSid=%r",
        payload.get("Body"),
        payload.get("From"),
        payload.get("To"),
        payload.get("MessageSid"),
    )

    # Twilio signature validation DISABLED for debug test
    # (re-enable by removing this early return block)
    debug_twiml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response>"
        "<Message>Debug reply from SupportPilot AI</Message>"
        "</Response>"
    )
    logger.info("DEBUG | returning immediate debug reply, skipping AI pipeline")
    return Response(content=debug_twiml, media_type="application/xml", status_code=200)
    # ------------------------------------------------------------------ #
    # END DEBUG MODE                                                       #
    # ------------------------------------------------------------------ #

    if not settings.twilio_configured:
        logger.info("WhatsApp webhook called while Twilio credentials are not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "WhatsApp integration is not configured. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM."
            ),
        )

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
        inbound = await whatsapp_adapter.parse_inbound(payload)
        user = await channel_identity_service.resolve_or_create(
            db=db,
            channel="whatsapp",
            identifier_value=inbound.sender_phone or inbound.sender_email.split("@")[0],
            display_name=inbound.sender_name,
        )

        pipeline_result = await run_inbound_support_pipeline(
            db=db,
            user=user,
            inbound=inbound,
            channel="whatsapp",
        )

        if pipeline_result.sender_phone and pipeline_result.response_text:
            send_result = await whatsapp_adapter.send_response_with_result(
                pipeline_result.sender_phone,
                pipeline_result.response_text,
            )
            msg_repo = MessageRepository(db)
            message = await msg_repo.get(pipeline_result.ai_message_id)
            metadata = dict(message.metadata_ or {}) if message else {}
            metadata["delivery"] = {
                "channel": "whatsapp",
                "provider": "twilio",
                "success": send_result.success,
                "sid": send_result.sid,
                "status": send_result.status,
                "error": send_result.error,
            }
            await msg_repo.update(pipeline_result.ai_message_id, {"metadata_": metadata})

            if not send_result.success:
                logger.warning(
                    "WhatsApp outbound send failed | conversation_id=%s message_id=%s error=%s",
                    pipeline_result.conversation_id,
                    pipeline_result.ai_message_id,
                    send_result.error,
                )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("WhatsApp inbound processing failed: %s", exc, exc_info=True)
        return Response(content="", status_code=200)

    return Response(
        content='<?xml version="1.0" encoding="UTF-8"?><Response></Response>',
        media_type="application/xml",
        status_code=200,
    )


@router.post(
    "/whatsapp/status",
    summary="Twilio WhatsApp delivery status callback",
    response_class=Response,
    status_code=204,
)
async def whatsapp_status_callback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_twilio_signature: str = Header(default="", alias="X-Twilio-Signature"),
) -> Response:
    """Accept Twilio delivery callbacks and log delivery outcomes safely."""
    payload: dict[str, Any] = dict(await request.form())

    if settings.twilio_configured and settings.ENVIRONMENT == "production":
        url = str(request.url)
        if not validate_twilio_signature(
            settings.TWILIO_AUTH_TOKEN, url, payload, x_twilio_signature
        ):
            logger.warning("Twilio status callback signature validation failed | url=%s", url)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid Twilio signature",
            )

    logger.info(
        "Twilio WhatsApp status callback | sid=%s status=%s to=%s error_code=%s",
        payload.get("MessageSid"),
        payload.get("MessageStatus"),
        payload.get("To"),
        payload.get("ErrorCode"),
    )
    await event_logger.log(
        db,
        "whatsapp_delivery_status",
        channel="whatsapp",
        details={
            "message_sid": payload.get("MessageSid"),
            "message_status": payload.get("MessageStatus"),
            "to": payload.get("To"),
            "error_code": payload.get("ErrorCode"),
            "error_message": payload.get("ErrorMessage"),
        },
    )
    return Response(status_code=204)


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
    """Receive and process a Gmail Pub/Sub push notification."""
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
        inbound = await email_adapter.parse_inbound(payload)
        user = await channel_identity_service.resolve_or_create(
            db=db,
            channel="email",
            identifier_value=inbound.sender_email,
            display_name=inbound.sender_name,
        )

        pipeline_result = await run_inbound_support_pipeline(
            db=db,
            user=user,
            inbound=inbound,
            channel="email",
        )

        if pipeline_result.response_text:
            thread_id = inbound.raw_payload.get("thread_id")
            await email_adapter.send_response(
                recipient=inbound.sender_email,
                message=pipeline_result.response_text,
                thread_id=thread_id,
                subject=inbound.subject,
            )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Gmail inbound processing failed: %s", exc, exc_info=True)
        return Response(status_code=204)

    return Response(status_code=204)
