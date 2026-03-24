"""Support form service — event-driven pipeline with dual-mode execution."""

from __future__ import annotations

import logging
import secrets
import time

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agent import support_agent
from app.core.config import settings
from app.repositories.conversation import ConversationRepository
from app.repositories.message import MessageRepository
from app.repositories.ticket import TicketRepository
from app.repositories.user import UserRepository
from app.schemas.support import SupportFormRequest, SupportSubmitResponse
from app.services.channel_identity import channel_identity_service
from app.services.event_logger import event_logger

logger = logging.getLogger(__name__)


class SupportService:
    """
    Handles the public support form end-to-end.

    Execution modes
    ---------------
    USE_KAFKA=false (default / local dev):
        Processes everything inline synchronously. AI agent runs, ticket is
        created, and the response is returned in the same HTTP response.
        Behavior is identical to the previous direct-call implementation.

    USE_KAFKA=true (production):
        Publishes a SupportFormEvent to the event bus (Kafka topic:
        webform_inbound). Returns a 202-style confirmation immediately.
        The MessageProcessorWorker picks up the event and runs the pipeline
        asynchronously. The customer's response is delivered via the channel
        adapter (web: stored in DB, accessible via /conversations endpoint).
    """

    async def submit_support_form(
        self,
        db: AsyncSession,
        data: SupportFormRequest,
    ) -> SupportSubmitResponse:
        """Process a web support form submission.

        Args:
            db: Active database session.
            data: Validated support form payload.

        Returns:
            SupportSubmitResponse with conversation_id, ticket_id, and AI reply.
        """
        if settings.USE_KAFKA:
            return await self._submit_async(db, data)
        return await self._submit_inline(db, data)

    # ------------------------------------------------------------------
    # Inline path (USE_KAFKA=false)
    # ------------------------------------------------------------------

    async def _submit_inline(
        self,
        db: AsyncSession,
        data: SupportFormRequest,
    ) -> SupportSubmitResponse:
        """Synchronous inline processing — no Kafka required."""
        # 1. Resolve/create user + Customer + CustomerIdentifier (web channel)
        user = await channel_identity_service.resolve_or_create(
            db=db,
            channel="web",
            identifier_value=data.email,
            display_name=data.name,
        )

        # 2. Create conversation
        conv_repo = ConversationRepository(db)
        conversation = await conv_repo.create({
            "user_id": user.id,
            "channel": "web",
            "subject": data.subject,
            "status": "active",
        })

        msg_repo = MessageRepository(db)

        # 3. Persist user message
        await msg_repo.create_message(
            conversation_id=conversation.id,
            sender_type="user",
            content=data.message,
        )

        # Log: support form submitted
        await event_logger.log(
            db,
            event_logger.SUPPORT_FORM_SUBMITTED,
            user_id=user.id,
            conversation_id=conversation.id,
            channel="web",
            priority=data.priority,
            details={"subject": data.subject, "category": data.category},
        )

        # 4. Run AI agent (full tool workflow: history → KB → ticket → respond)
        t0 = time.monotonic()
        ai_result = await support_agent.run(
            db=db,
            user_id=user.id,
            conversation_id=conversation.id,
            user_message=data.message,
            conversation_history=[],
        )
        response_ms = (time.monotonic() - t0) * 1000

        # 5. Persist AI reply with full AI signals
        await msg_repo.create_message(
            conversation_id=conversation.id,
            sender_type="ai",
            content=ai_result.response,
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
            user_id=user.id,
            conversation_id=conversation.id,
            channel="web",
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
            await conv_repo.update(conversation.id, {"status": "escalated"})
            await event_logger.log(
                db,
                event_logger.ISSUE_ESCALATED,
                user_id=user.id,
                conversation_id=conversation.id,
                channel="web",
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
                conversation_id=conversation.id,
                channel="web",
                details={"intent": ai_result.intent},
            )

        # 6. Auto-create ticket (agent may also create one via tool; this is
        #    a fallback to ensure a ticket always exists after form submission)
        ticket_repo = TicketRepository(db)
        existing_tickets = await ticket_repo.get_by_user(user.id, skip=0, limit=1)
        conv_tickets = [t for t in existing_tickets if t.conversation_id == conversation.id]

        if conv_tickets:
            ticket = conv_tickets[0]
        else:
            fallback_ticket_data: dict = {
                "user_id": user.id,
                "conversation_id": conversation.id,
                "title": data.subject,
                "description": data.message,
                "category": getattr(ai_result, "category", data.category),
                "priority": getattr(ai_result, "priority", data.priority),
                "sentiment": getattr(ai_result, "sentiment", None),
                "urgency": getattr(ai_result, "urgency", None),
            }
            if ai_result.should_escalate and ai_result.escalation_reason:
                fallback_ticket_data["escalation_reason"] = ai_result.escalation_reason
            ticket = await ticket_repo.create(fallback_ticket_data)
            await event_logger.log(
                db,
                event_logger.TICKET_CREATED,
                user_id=user.id,
                conversation_id=conversation.id,
                ticket_id=ticket.id,
                channel="web",
                priority=ticket.priority,
                details={"category": ticket.category, "title": ticket.title},
            )

        # 7. Record metrics (non-blocking)
        try:
            from app.repositories.agent_metrics import AgentMetricsRepository
            metrics_repo = AgentMetricsRepository(db)
            await metrics_repo.record({
                "conversation_id": conversation.id,
                "user_id": user.id,
                "channel": "web",
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
            logger.warning("Failed to record metrics: %s", exc)

        confirmation = (
            f"Thank you for contacting SupportPilot, {data.name}. "
            f"Your request has been received and a ticket (#{ticket.id[:8].upper()}) "
            "has been created. Our team will follow up with you shortly."
        )

        return SupportSubmitResponse(
            conversation_id=conversation.id,
            ticket_id=ticket.id,
            confirmation_message=confirmation,
            ai_response=ai_result.response,
        )

    # ------------------------------------------------------------------
    # Async Kafka path (USE_KAFKA=true)
    # ------------------------------------------------------------------

    async def _submit_async(
        self,
        db: AsyncSession,
        data: SupportFormRequest,
    ) -> SupportSubmitResponse:
        """
        Publish form event to Kafka; worker processes asynchronously.

        In this mode:
        - A placeholder conversation and ticket are created immediately
          so the caller has IDs to reference.
        - The event is published to the webform_inbound topic.
        - The MessageProcessorWorker picks it up and runs the AI pipeline.
        - The AI response is stored in the conversation when ready.
        """
        import uuid as _uuid
        from app.events.bus import get_event_bus
        from app.events.schemas import SupportFormEvent, make_event
        from app.events.topics import Topic

        user = await channel_identity_service.resolve_or_create(
            db=db,
            channel="web",
            identifier_value=data.email,
            display_name=data.name,
        )

        # Create placeholder conversation
        conv_repo = ConversationRepository(db)
        conversation = await conv_repo.create({
            "user_id": user.id,
            "channel": "web",
            "subject": data.subject,
            "status": "active",
        })

        # Create placeholder ticket immediately so caller has a reference
        ticket_repo = TicketRepository(db)
        ticket = await ticket_repo.create({
            "user_id": user.id,
            "conversation_id": conversation.id,
            "title": data.subject,
            "description": data.message,
            "category": data.category,
            "priority": data.priority,
        })

        # Publish to event bus (Kafka in production)
        event = make_event(
            SupportFormEvent,
            channel="web",
            name=data.name,
            email=data.email,
            subject=data.subject,
            message=data.message,
            category=data.category,
            priority=data.priority,
        )

        bus = get_event_bus()
        await bus.publish(Topic.WEBFORM_INBOUND, event)

        logger.info(
            "SupportFormEvent queued | event_id=%s conversation_id=%s",
            event.event_id,
            conversation.id,
        )

        return SupportSubmitResponse(
            conversation_id=conversation.id,
            ticket_id=ticket.id,
            confirmation_message=(
                f"Thank you, {data.name}. Your request has been received "
                f"(ticket #{ticket.id[:8].upper()}). "
                "Our AI agent is processing your request and will respond shortly."
            ),
            ai_response=(
                "Your request has been queued and will be processed by our AI agent. "
                "You will receive a response in your conversation thread shortly."
            ),
        )


support_service = SupportService()
