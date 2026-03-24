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
Your ONLY job is to execute the following tools in order to log this interaction:

  1. get_customer_history(user_id)      — ALWAYS first
  2. search_knowledge_base(query)       — ALWAYS second
  3. create_ticket(title, description, category, priority) — ALWAYS third
  4. escalate_to_human(reason, urgency) — ONLY if escalation_required=true (see context)
  5. send_response(message, intent, confidence) — ALWAYS last; terminates the loop

IMPORTANT:
- For create_ticket: use the category and priority that match the customer's issue.
- For send_response: the message you provide will be overridden by the pre-determined
  response. Just pass a brief summary. Set intent and confidence accurately.
- DO NOT make up information about the customer's history.
- Follow the tool order exactly.

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
            escalation_note = escalation_engine.build_escalation_note(esc_decision)
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
        # Phase 2 — Tool loop: side effects (history, KB, ticket, escalate)
        # The effective_decision (merged LLM + escalation engine) is injected
        # so send_response and escalate_to_human use the final verdict.
        # ------------------------------------------------------------------
        ctx = AgentContext(db=db, user_id=user_id, conversation_id=conversation_id)
        ctx.predecided = effective_decision  # inject merged decision

        executor = ToolExecutor()
        client = get_openai_client()
        messages = self._build_initial_messages(conversation_history, user_message, effective_decision)

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
            tools_called=ctx.tools_called,
            iterations=ctx.iterations,
            kb_articles_found=ctx.kb_articles_found,
            ticket_created=ctx.ticket_created,
        )

    def _build_initial_messages(
        self,
        conversation_history: list[dict],
        user_message: str,
        decision: Any,
    ) -> list[dict]:
        """Build the initial messages array for the tool loop.

        Includes the system prompt, up to the last 6 history entries, the new
        user message, and a context note with the pre-determined decision so the
        tool loop agent can create an accurately-categorised ticket.
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

        # Inject decision context so the tool loop creates the right ticket
        messages.append({
            "role": "system",
            "content": (
                f"[Decision context] "
                f"intent={decision.intent} category={decision.category} "
                f"priority={decision.priority} urgency={decision.urgency} "
                f"escalation_required={decision.escalate} "
                f"confidence={decision.confidence:.2f}"
            ),
        })

        return messages


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

support_agent = SupportAgent()
