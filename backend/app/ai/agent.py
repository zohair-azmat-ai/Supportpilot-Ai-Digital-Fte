"""
SupportPilot AI Agent — LLM-driven structured support decision engine.

Architecture (Level 4):

  Step 1 — SupportDecisionEngine
    ├── Calls OpenAI with a structured JSON-mode prompt
    ├── Receives and validates a SupportDecision (reply, intent, category,
    │   priority, sentiment, urgency, confidence, escalate)
    └── This is the sole source of truth for the customer-facing reply.

  Step 2 (this upgrade) — ConversationContextBuilder
    ├── Derives repeat/frustration signals from conversation history
    ├── Fetches cross-session user tickets/conversations from DB
    └── Injects a [CONVERSATION CONTEXT] block into the LLM prompt

  Step 3 — Tool loop (side effects only)
    ├── get_customer_history  — loads prior tickets/conversations for context
    ├── search_knowledge_base — retrieves relevant help articles
    ├── create_ticket         — logs the interaction with correct category/priority
    ├── escalate_to_human     — flags conversation if decision.escalate is True
    └── send_response         — terminates the loop (uses decision engine's reply)

Returns AIResponse — same type as before, fully backward-compatible.
New fields: category, priority, sentiment, urgency (from SupportDecision).
"""

from __future__ import annotations

import json as _json
import logging
import re
from typing import Any

from app.ai.client import get_openai_client
from app.ai.context_builder import context_builder
from app.ai.decision_engine import decision_engine
from app.ai.escalation_engine import EscalationDecision, escalation_engine
from app.ai.service import AIResponse, _build_fallback_response
from app.ai.tools import TOOL_DEFINITIONS, AgentContext, ToolExecutor
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent system prompt (used by the tool-loop — side effects only)
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """\
You are SupportPilot AI — running in side-effects mode.

The customer's reply has already been determined by the decision engine.
Your ONLY job is to execute the following tools to log this interaction:

  1. get_customer_history(user_id)      — ALWAYS first
  2. search_knowledge_base(query)       — ALWAYS second
  3. create_ticket(title, description, category, priority)
       — ONLY when should_create_ticket=true in the decision context (see below).
       — SKIP this tool entirely when should_create_ticket=false.
  4. escalate_to_human(reason, urgency) — ONLY if escalation_required=true (see context)
  5. send_response(message, intent, confidence) — ALWAYS last; terminates the loop

TICKET CREATION POLICY — create_ticket is ONLY required when ANY of these are true:
  a) escalation_required=true
  b) repeated_issue=true
  c) category is "billing" or "complaint"
  d) category is "technical" and it is NOT the first contact turn

DO NOT call create_ticket for:
  - Greetings (hi, hello, hey, etc.)
  - First-contact login / account guidance (password reset, account help on turn 1)
  - Simple informational or general questions with no reported failure

When should_create_ticket=false: go directly from search_knowledge_base to send_response.

IMPORTANT:
- For create_ticket: use the category and priority that match the customer's issue.
- For send_response: the message you provide will be overridden by the pre-determined
  response. Just pass a brief summary. Set intent and confidence accurately.
- DO NOT make up information about the customer's history.

TOOL REFERENCE
- get_customer_history(user_id): Returns prior tickets and conversations.
- search_knowledge_base(query): Keyword search across help articles.
- create_ticket(title, description, category, priority):
    Categories: technical | billing | account | general | complaint | feature_request
    Priorities: low | medium | high | urgent
- escalate_to_human(reason, urgency): Flags conversation for human takeover.
    Urgency: normal | urgent
- send_response(message, intent, confidence):
    Intents: general | technical | billing | account | complaint | feature_request | urgent
    Confidence: 0.0–1.0
"""


# ---------------------------------------------------------------------------
# SupportAgent — main entry point
# ---------------------------------------------------------------------------


class SupportAgent:
    """Tool-calling agent with LLM-driven structured decision engine.

    Every customer message is processed in two phases:
      1. SupportDecisionEngine generates a validated SupportDecision (reply + metadata).
      2. The tool loop runs side effects: ticket creation, KB search, escalation.

    Returns AIResponse — fully backward-compatible with existing callers.
    """

    MAX_ITERATIONS = 8

    async def run(
        self,
        db: Any,
        user_id: str,
        conversation_id: str,
        user_message: str,
        conversation_history: list[dict],
    ) -> AIResponse:
        """Process one customer message through the full decision + side-effect pipeline.

        Args:
            db: AsyncSession database session.
            user_id: Customer's user ID.
            conversation_id: Current conversation ID.
            user_message: Latest message text from the customer.
            conversation_history: Prior messages [{sender_type, content}, ...].

        Returns:
            AIResponse — always valid, never raises.
        """
        # ------------------------------------------------------------------
        # Phase 1a — Build conversation context (memory + repeat signals)
        # Safe fallback: if context build fails, ctx=None and the decision
        # engine runs without context (Step 1 behaviour as fallback).
        # ------------------------------------------------------------------
        conv_context = None
        try:
            conv_context = await context_builder.build(
                db=db,
                user_id=user_id,
                user_message=user_message,
                conversation_history=conversation_history,
            )
            logger.info(
                "Context: turn=%d repeated=%s frustrated=%s "
                "failed_attempts=%d open_ticket=%s | conversation=%s",
                conv_context.message_count_in_session + 1,
                conv_context.repeated_issue,
                conv_context.user_frustrated,
                conv_context.previous_failed_attempts,
                conv_context.related_open_ticket_exists,
                conversation_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Context build failed (non-fatal): %s", exc)

        # ------------------------------------------------------------------
        # Phase 1a.5 — Repeat-keyword safety net
        # The context builder derives attempt counts from keyword overlap in
        # prior turns.  When prior messages were very short, the overlap may
        # be missed.  This safety net catches explicit repeat signals in the
        # CURRENT message and bumps the count so strategy + escalation logic
        # operate on accurate data.
        # ------------------------------------------------------------------
        if (
            conv_context is not None
            and not conv_context.is_first_contact
            and self._detect_repeat_keywords(user_message)
            and conv_context.previous_failed_attempts == 0
        ):
            conv_context.previous_failed_attempts = 1
            conv_context.repeated_issue = True
            conv_context.response_strategy = "second_attempt"
            logger.info(
                "Repeat keywords in message — bumped attempts to 1, strategy=second_attempt "
                "| conversation=%s",
                conversation_id,
            )

        # ------------------------------------------------------------------
        # Phase 1b — Decision engine: generates structured reply + metadata
        # ------------------------------------------------------------------
        try:
            decision = await decision_engine.run(
                user_message, conversation_history, context=conv_context
            )
        except Exception as exc:  # noqa: BLE001 — absolute safety net
            logger.error("Decision engine failed: %s", exc, exc_info=True)
            fallback = _build_fallback_response(user_message)
            return fallback

        logger.info(
            "Decision: intent=%s category=%s priority=%s sentiment=%s "
            "urgency=%s confidence=%.2f escalate=%s | conversation=%s",
            decision.intent, decision.category, decision.priority,
            decision.sentiment, decision.urgency, decision.confidence,
            decision.escalate, conversation_id,
        )

        # ------------------------------------------------------------------
        # Phase 1c — Escalation engine: deterministic post-processing
        # Supplements/overrides LLM escalation with rule-based hard checks
        # (security, legal, explicit human request, frustration, etc.)
        # ------------------------------------------------------------------
        esc_decision: EscalationDecision = escalation_engine.evaluate(
            context=conv_context,
            llm_decision=decision,
            user_message=user_message,
        )

        # Merge escalation engine result into the decision.
        # If the engine upgrades non-escalation → escalation, append a short
        # natural-language note so the reply doesn't silently contradict the
        # escalation that's about to happen.
        upgraded_escalation = esc_decision.escalate and not decision.escalate
        if upgraded_escalation:
            escalation_note = escalation_engine.build_escalation_note(esc_decision, conv_context)
            updated_reply = f"{decision.reply}\n\n{escalation_note}"
            effective_decision = decision.model_copy(update={
                "reply": updated_reply,
                "escalate": True,
                "escalation_reason": esc_decision.escalation_reason,
            })
        else:
            effective_decision = decision.model_copy(update={
                "escalate": esc_decision.escalate,
                "escalation_reason": (
                    esc_decision.escalation_reason or decision.escalation_reason
                ),
            })

        logger.info(
            "Escalation: escalate=%s level=%s cause=%s | conversation=%s",
            esc_decision.escalate, esc_decision.escalation_level,
            esc_decision.escalation_cause, conversation_id,
        )

        # ------------------------------------------------------------------
        # Phase 1d — First-contact reply sanitization (final safety net)
        # Removes any escalation / history-assumption language that the LLM
        # may have generated despite the first-contact guidance in the prompt.
        # ------------------------------------------------------------------
        if conv_context is not None and conv_context.is_first_contact:
            sanitized_reply = self._sanitize_first_contact_reply(effective_decision.reply)
            if sanitized_reply != effective_decision.reply:
                logger.info(
                    "Reply sanitized for first contact | conversation=%s",
                    conversation_id,
                )
                effective_decision = effective_decision.model_copy(
                    update={"reply": sanitized_reply}
                )

        # ------------------------------------------------------------------
        # Phase 2 — Tool loop: side effects (history, KB, ticket, escalate)
        # ------------------------------------------------------------------

        # Determine whether a ticket should be created for this interaction.
        # Tickets are only needed when there is a real reportable problem:
        #   - escalation triggered
        #   - repeated / persistent issue
        #   - billing or complaint categories (always trackable)
        #   - technical issue on a non-first-contact turn
        # Greetings, first-contact account guidance, and simple questions
        # do NOT warrant ticket creation — creating tickets for them is what
        # caused every follow-up message to falsely see an "open ticket".
        _is_first = conv_context.is_first_contact if conv_context else True
        _repeated = conv_context.repeated_issue if conv_context else False
        should_create_ticket: bool = (
            esc_decision.escalate
            or _repeated
            or effective_decision.category in ("billing", "complaint")
            or (effective_decision.category == "technical" and not _is_first)
        )
        logger.info(
            "Ticket policy: should_create_ticket=%s "
            "(escalate=%s repeated=%s category=%s first_contact=%s) | conversation=%s",
            should_create_ticket,
            esc_decision.escalate, _repeated,
            effective_decision.category, _is_first,
            conversation_id,
        )

        ctx = AgentContext(db=db, user_id=user_id, conversation_id=conversation_id)
        ctx.predecided = effective_decision  # inject merged decision
        ctx.should_create_ticket = should_create_ticket

        if conv_context is not None:
            ctx.similar_issue_found = conv_context.similar_issue_found
            ctx.unresolved_similar_ticket_ids = (
                conv_context.related_ticket_ids
                if conv_context.unresolved_similar_issue_exists
                else []
            )

        executor = ToolExecutor()
        client = get_openai_client()
        messages = self._build_initial_messages(
            conversation_history, user_message, effective_decision, should_create_ticket
        )

        try:
            for iteration in range(self.MAX_ITERATIONS):
                ctx.iterations = iteration + 1
                logger.debug("Tool loop iteration %d/%d", iteration + 1, self.MAX_ITERATIONS)

                response = await client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,  # type: ignore[arg-type]
                    tools=TOOL_DEFINITIONS,  # type: ignore[arg-type]
                    tool_choice="required",
                    temperature=0.2,
                    max_tokens=800,
                )

                msg = response.choices[0].message

                if not msg.tool_calls:
                    logger.warning("Tool loop: no tool calls on iteration %d", iteration)
                    if not ctx.final_response:
                        ctx.final_response = effective_decision.reply
                    break

                messages.append({
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                        for tc in msg.tool_calls
                    ],
                })

                for tool_call in msg.tool_calls:
                    tool_name = tool_call.function.name
                    args = _json.loads(tool_call.function.arguments)

                    logger.info(
                        "Tool: %s | args=%s | conversation=%s",
                        tool_name, list(args.keys()), conversation_id,
                    )

                    result = await executor.execute(tool_name, args, ctx)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })

                    if tool_name == "send_response" and ctx.final_response:
                        break

                if ctx.final_response:
                    break

            if not ctx.final_response:
                logger.warning(
                    "Tool loop ended after %d iterations without send_response",
                    self.MAX_ITERATIONS,
                )
                ctx.final_response = effective_decision.reply

        except Exception as exc:  # noqa: BLE001
            logger.error("Tool loop failed: %s", exc, exc_info=True)
            # Decision engine already gave us a valid reply; continue with it.

        # ------------------------------------------------------------------
        # If effective_decision says escalate but tool loop didn't call
        # escalate_to_human, perform it directly so conversation status is
        # always consistent with the final escalation verdict.
        # ------------------------------------------------------------------
        if effective_decision.escalate and not ctx.should_escalate:
            try:
                from app.repositories.conversation import ConversationRepository
                conv_repo = ConversationRepository(db)
                await conv_repo.update(conversation_id, {"status": "escalated"})
                ctx.should_escalate = True
                ctx.escalation_reason = effective_decision.escalation_reason
            except Exception as exc:  # noqa: BLE001
                logger.warning("Direct escalation update failed: %s", exc)

        # ------------------------------------------------------------------
        # Build final AIResponse — effective_decision is source of truth
        # (LLM decision merged with escalation engine verdict)
        # ------------------------------------------------------------------
        return AIResponse(
            response=effective_decision.reply,
            intent=effective_decision.intent,
            confidence=effective_decision.confidence,
            should_escalate=effective_decision.escalate,
            escalation_reason=effective_decision.escalation_reason,
            escalation_level=esc_decision.escalation_level,
            escalation_cause=esc_decision.escalation_cause,
            category=effective_decision.category,
            priority=effective_decision.priority,
            sentiment=effective_decision.sentiment,
            urgency=effective_decision.urgency,
            similar_issue_detected=(
                conv_context.similar_issue_found if conv_context is not None else False
            ),
            tools_called=ctx.tools_called,
            iterations=ctx.iterations,
            kb_articles_found=ctx.kb_articles_found,
            ticket_created=ctx.ticket_created,
        )

    # ------------------------------------------------------------------
    # Repeat-keyword detection (safety net for context builder misses)
    # ------------------------------------------------------------------

    # Explicit repeat-attempt signals that should always be caught even when
    # the context builder's keyword-overlap scoring misses them.
    _REPEAT_KEYWORDS: frozenset = frozenset({
        "still not working", "still doesn't work", "still not",
        "still can't", "still cannot", "tried again", "tried it again",
        "same issue again", "again same issue", "again same problem",
        "tried everything", "nothing works", "not working again",
        "happening again", "still happening", "still broken",
        "already tried", "tried that already", "did that already",
    })

    @classmethod
    def _detect_repeat_keywords(cls, message: str) -> bool:
        """Return True if the message contains explicit repeat-attempt signals."""
        msg = message.lower()
        return any(kw in msg for kw in cls._REPEAT_KEYWORDS)

    # ------------------------------------------------------------------
    # First-contact reply sanitizer
    # ------------------------------------------------------------------

    # Any of these phrases appearing in a first-contact reply means the LLM
    # incorrectly assumed prior history.  Replace the entire reply rather than
    # stripping fragments — a surgically cleaned sentence is still wrong.
    _FIRST_CONTACT_BAD_PHRASES: tuple[str, ...] = (
        "still facing",
        "still experiencing",
        "still having this",
        "ongoing issue",
        "ongoing problem",
        "existing ticket",
        "have an open ticket",
        "has an open ticket",
        "issue persists",
        "issue is persisting",
        "issue continues",
        "this issue continues",
        "previous attempts",
        "prior attempts",
        "as mentioned earlier",
        "as we discussed",
        "as discussed earlier",
        "i can see this hasn't",
        "i can see you've been",
        "since this issue",
        "open ticket",         # catches "you have an open ticket", "the open ticket"
        "existing issue",
    )

    # Neutral clarification returned whenever the above guard fires
    _FIRST_CONTACT_NEUTRAL_REPLY: str = (
        "Happy to help! Can you tell me what's going on?"
    )

    @classmethod
    def _sanitize_first_contact_reply(cls, reply: str) -> str:
        """Final safety net for first-contact replies.

        If the reply contains ANY phrase that implies repeated history or a
        prior unresolved issue, replace the entire reply with a neutral
        clarification prompt.  Stripping fragments leaves broken sentences —
        a full replacement is safer and cleaner.
        """
        reply_lower = reply.lower()
        for phrase in cls._FIRST_CONTACT_BAD_PHRASES:
            if phrase in reply_lower:
                logger.info(
                    "First-contact reply contained bad phrase %r — replacing with neutral reply",
                    phrase,
                )
                return cls._FIRST_CONTACT_NEUTRAL_REPLY
        return reply

    def _build_initial_messages(
        self,
        conversation_history: list[dict],
        user_message: str,
        decision: Any,
        should_create_ticket: bool = True,
    ) -> list[dict]:
        """Build the initial messages array for the tool loop.

        Includes the system prompt, up to the last 6 history entries, the new
        user message, and a context note with the pre-determined decision and
        ticket-creation policy flag so the tool loop follows the correct path.
        """
        messages: list[dict] = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]

        for entry in conversation_history[-6:]:
            sender = entry.get("sender_type", "user")
            content = entry.get("content", "")
            if not content:
                continue
            if sender == "user":
                messages.append({"role": "user", "content": content})
            elif sender in ("ai", "agent"):
                try:
                    parsed = _json.loads(content)
                    content = parsed.get("reply") or parsed.get("response", content)
                except Exception:  # noqa: BLE001
                    pass
                messages.append({"role": "assistant", "content": content})

        messages.append({"role": "user", "content": user_message})

        # Inject decision context so the tool loop uses the right category/priority
        # and knows whether to call create_ticket.
        messages.append({
            "role": "system",
            "content": (
                f"[Decision context] "
                f"intent={decision.intent} category={decision.category} "
                f"priority={decision.priority} urgency={decision.urgency} "
                f"escalation_required={decision.escalate} "
                f"confidence={decision.confidence:.2f} "
                f"should_create_ticket={should_create_ticket}"
            ),
        })

        return messages


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

support_agent = SupportAgent()
