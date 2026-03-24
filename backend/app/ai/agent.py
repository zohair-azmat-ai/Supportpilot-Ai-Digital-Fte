"""
SupportPilot AI Agent — tool-based agentic support system.

The agent runs a multi-step reasoning loop using OpenAI function calling:
  1. get_customer_history  (always first)
  2. search_knowledge_base (always second)
  3. create_ticket         (always third)
  4. escalate_to_human     (if needed)
  5. send_response         (always last — terminates loop)

The agent loop continues until send_response is called or max_iterations is reached.
Returns AIResponse — same type as the old AIService, so callers are unchanged.
"""

from __future__ import annotations

import json as _json
import logging
from typing import Any

from app.ai.client import get_openai_client
from app.ai.service import AIResponse, _build_fallback_response
from app.ai.tools import TOOL_DEFINITIONS, AgentContext, ToolExecutor
from app.core.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent system prompt
# ---------------------------------------------------------------------------

AGENT_SYSTEM_PROMPT = """You are SupportPilot AI, a professional customer support agent for SupportPilot. \
Your role is to assist customers efficiently and empathetically by following a strict tool-based workflow.

## MANDATORY TOOL EXECUTION ORDER
You MUST call tools in this exact order every time — no exceptions:
  1. get_customer_history  — ALWAYS the very first tool. Retrieves the customer's prior tickets and conversations so you have full context.
  2. search_knowledge_base — ALWAYS the second tool. Search for relevant help articles using keywords from the customer's message.
  3. create_ticket         — ALWAYS the third tool. Create a support ticket to log this interaction, UNLESS a ticket already exists for this conversation_id.
  4. escalate_to_human     — Call this ONLY when escalation is required (see criteria below). Skip if not needed.
  5. send_response         — ALWAYS the last tool. Deliver the final reply to the customer. This terminates your loop.

You MUST NOT write a direct reply to the customer. The ONLY way to respond is through the send_response tool.

## ESCALATION CRITERIA
Call escalate_to_human (before send_response) when any of the following apply:
- The customer explicitly requests to speak with a human agent
- The issue involves a billing dispute or charge reversal
- Legal threats or regulatory mentions (e.g., "lawyer", "GDPR", "sue")
- Security concerns (account compromise, suspected fraud)
- High emotional distress or repeated expressions of frustration
- Customer indicates the issue is still unresolved ("still", "again", "not fixed", "same issue")
- The same topic has been raised by the customer multiple times in this conversation
- The issue cannot be resolved with available knowledge base information
- VIP or enterprise customer with a critical production outage

## TOOL REFERENCE
- get_customer_history(user_id): Returns up to 5 recent tickets and 3 recent conversations for context.
- search_knowledge_base(query): Keyword search across help articles. Use clear, specific terms from the customer's message.
- create_ticket(title, description, category, priority): Logs the interaction. Choose category and priority carefully:
    Categories: technical, billing, account, general, complaint, feature_request
    Priorities: low (general questions), medium (inconvenience), high (service disruption), urgent (critical outage or security)
- escalate_to_human(reason, urgency): Flags conversation for human takeover and sets status to 'escalated'.
    Urgency: normal or urgent
- send_response(message, intent, confidence): Sends the reply and ends the agent loop.
    Intents: general, technical, billing, account, complaint, feature_request, urgent
    Confidence: 0.0–1.0 representing your certainty in the intent classification

## TONE GUIDELINES
- Professional and empathetic: acknowledge the customer's frustration before diving into solutions
- Concise: aim for clear, direct answers — avoid unnecessary filler phrases
- Reassuring: where resolution is uncertain, explain next steps clearly
- Personalised: reference information from the customer's history where relevant
- Never make promises about outcomes (e.g., "we will definitely refund you")

## INTENT CATEGORIES
- general: general enquiries, greetings, feedback not fitting other categories
- technical: bugs, errors, performance issues, integration problems
- billing: invoices, charges, refunds, subscription changes
- account: login issues, password resets, profile changes, permissions
- complaint: expressions of dissatisfaction with service or product
- feature_request: suggestions for new features or improvements
- urgent: critical service outages, security incidents, or high-severity technical failures

Always be helpful, accurate, and professional. Follow the tool order without deviation.
"""


# ---------------------------------------------------------------------------
# Pre-flight intent classification + response selection
# ---------------------------------------------------------------------------

# --- Keyword sets ---

_GRATITUDE_KEYWORDS = frozenset({
    "thank you", "thanks", "appreciate it", "appreciated", "thank u",
    "many thanks", "cheers", "thx", "ty", "tysm", "grateful",
    "that helped", "that's helpful", "that was helpful", "problem solved",
    "issue resolved", "all good", "sorted", "got it", "perfect thanks",
})

_ACCOUNT_KEYWORDS = frozenset({
    "password", "reset", "login", "log in", "sign in", "signin",
    "credential", "credentials", "locked out", "account", "access denied",
    "can't login", "cannot login", "forgot password",
})

_REPEATED_ISSUE_KEYWORDS = frozenset({
    "already", "still", "tried", "again", "same", "still not",
    "not working", "issue not solved", "not fixed", "same problem",
    "same issue", "unresolved", "keeps happening", "nothing works",
    "didn't help", "didn't fix", "did not help", "did not fix",
    "no solution", "still broken", "still failing", "happening again",
})

# Common words excluded from topic-overlap memory check
_STOP_WORDS = frozenset({
    "i", "my", "me", "the", "a", "an", "is", "it", "to", "have", "has",
    "am", "are", "was", "be", "of", "in", "for", "and", "or", "but",
    "that", "this", "with", "on", "at", "can", "you", "your", "we",
    "not", "no", "do", "don", "get", "got", "help", "please", "hi",
})

# --- Response variant pools (3 variants each, never repeat the last reply) ---

_GRATITUDE_VARIANTS = [
    "You're welcome! 😊\nIf you need any further help, feel free to reach out anytime.",
    "Happy to help! 😊\nDon't hesitate to get in touch if anything else comes up.",
    "Glad I could assist! 😊\nWe're here whenever you need us — take care!",
]

_ACCOUNT_TROUBLESHOOT_VARIANTS = [
    (
        "I can help you get back into your account. Here are the steps to try:\n\n"
        "1. Click **Forgot Password** on the login page\n"
        "2. Enter your registered email address and submit\n"
        "3. Check your inbox — and your spam/junk folder — for a reset link\n"
        "4. If the email doesn't arrive within 5 minutes, make sure you're using "
        "the email address you signed up with\n\n"
        "Let me know if any of these work, or if the problem continues."
    ),
    (
        "Happy to help you sort out your login. Please try the following:\n\n"
        "• Go to the sign-in page and select **Reset Password**\n"
        "• Enter your email — a reset link will arrive within a few minutes\n"
        "• Check both inbox and spam; sometimes these emails get filtered\n"
        "• Try a different browser or clear your cache if the link doesn't work\n\n"
        "Still stuck after trying these? Just let me know and I'll escalate this right away."
    ),
    (
        "Let's get your account access sorted. A few things to check:\n\n"
        "1. Use the **Forgot Password** option on the login screen\n"
        "2. Confirm you're entering the email you originally registered with\n"
        "3. Check spam/junk for the password reset email\n"
        "4. Try opening the reset link in an incognito/private window\n\n"
        "If none of these resolve it, reply here and I'll connect you with an agent."
    ),
]

_ACCOUNT_ESCALATION_VARIANTS = [
    (
        "I understand you've already tried resolving this issue. "
        "Since it's still happening, I'm escalating this to a human support agent "
        "who will assist you further."
    ),
    (
        "I can see you've been working on this for a while — I'm sorry it hasn't been "
        "resolved yet. I'm connecting you with a human support agent now who will "
        "personally take this forward."
    ),
    (
        "Since the issue is persisting despite your attempts, I'm escalating this "
        "immediately. A human support agent will reach out to you shortly."
    ),
]

_GENERAL_ESCALATION_VARIANTS = [
    (
        "I understand the issue is still not resolved. "
        "I'm escalating this to a human support agent who will assist you further shortly."
    ),
    (
        "I'm sorry to hear this is still happening — I'm connecting you with a human "
        "support agent right now. They will be with you shortly."
    ),
    (
        "Since this is an ongoing issue, I'm passing this to a human support agent "
        "who can give it the full attention it deserves."
    ),
]


# --- Helpers ---

def _get_last_ai_response(conversation_history: list[dict]) -> str:
    """Return the content of the most recent AI message in history, or empty string."""
    for m in reversed(conversation_history):
        if m.get("sender_type") in ("ai", "agent") and m.get("content"):
            return m["content"].strip()
    return ""


def _pick_variant(variants: list[str], conversation_history: list[dict]) -> str:
    """Choose a response variant, preferring one different from the last AI reply.

    Cycles deterministically through available options so the customer
    never sees the exact same text twice in a row.
    """
    last_ai = _get_last_ai_response(conversation_history)
    candidates = [v for v in variants if v.strip() != last_ai]
    pool = candidates if candidates else variants
    return pool[len(conversation_history) % len(pool)]


# --- Main classification function ---

def _classify_message_signals(
    user_message: str,
    conversation_history: list[dict],
) -> dict:
    """Classify the message and conversation into intent + repeated_issue signals.

    Checks two dimensions:

    * **intent** — ``"account_issue"`` if login/password/credential keywords are
      present; ``"general"`` otherwise.

    * **repeated_issue** — ``True`` when:
      - The message contains an explicit frustration/retry phrase (e.g. "already
        tried", "still not working", "same issue"), OR
      - The topic has appeared in ≥2 of the last 6 user turns (memory signal).

    Returns a dict with keys ``intent`` (str) and ``repeated_issue`` (bool).
    Safe when ``user_message`` is empty or ``conversation_history`` is empty.
    """
    msg = user_message.lower().strip()
    if not msg:
        return {"intent": "general", "repeated_issue": False}

    intent = "account_issue" if any(k in msg for k in _ACCOUNT_KEYWORDS) else "general"

    # Signal A: explicit repeated-issue keyword
    repeated = any(kw in msg for kw in _REPEATED_ISSUE_KEYWORDS)

    # Signal B: topic repetition across history (memory check)
    if not repeated:
        prior_user_msgs = [
            m.get("content", "").lower()
            for m in conversation_history
            if m.get("sender_type") == "user" and m.get("content")
        ]
        if len(prior_user_msgs) >= 2:
            current_words = set(msg.split()) - _STOP_WORDS
            if len(current_words) >= 2:
                overlap_count = sum(
                    1
                    for prev in prior_user_msgs[-6:]
                    if len((set(prev.split()) - _STOP_WORDS) & current_words) >= 2
                )
                if overlap_count >= 2:
                    repeated = True

    return {"intent": intent, "repeated_issue": repeated}


# ---------------------------------------------------------------------------
# SupportAgent — main entry point
# ---------------------------------------------------------------------------


class SupportAgent:
    """Tool-calling agent that replaces the direct AIService.generate_response() call.

    Returns AIResponse so existing callers require no changes.
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
        """Run the full agent workflow for one customer message.

        Args:
            db: AsyncSession database session.
            user_id: ID of the customer sending the message.
            conversation_id: ID of the current conversation.
            user_message: The latest message text from the customer.
            conversation_history: List of prior message dicts with
                ``sender_type`` and ``content`` keys (oldest first).

        Returns:
            AIResponse compatible with the existing service interface.
            Gracefully falls back to a context-aware response on any error.
        """
        # ------------------------------------------------------------------
        # Pre-flight classification — runs before any OpenAI call.
        # Handles clear-cut cases immediately; ambiguous ones go to OpenAI.
        # ------------------------------------------------------------------

        # Gratitude check — evaluated first; overrides all other intents.
        # A closing message should never trigger issue analysis or escalation.
        if user_message and any(kw in user_message.lower() for kw in _GRATITUDE_KEYWORDS):
            logger.info("Pre-flight: gratitude | conversation=%s", conversation_id)
            return AIResponse(
                response=_pick_variant(_GRATITUDE_VARIANTS, conversation_history),
                intent="gratitude",
                confidence=0.95,
                should_escalate=False,
            )

        signals = _classify_message_signals(user_message, conversation_history)
        intent = signals["intent"]
        repeated = signals["repeated_issue"]

        if intent == "account_issue" and repeated:
            # Account issue + user has already tried → escalate with empathy
            reason = "Account issue persisting after user's own troubleshooting attempts"
            logger.info("Pre-flight: account+repeated | conversation=%s", conversation_id)
            return AIResponse(
                response=_pick_variant(_ACCOUNT_ESCALATION_VARIANTS, conversation_history),
                intent="account",
                confidence=0.9,
                should_escalate=True,
                escalation_reason=reason,
            )

        if repeated:
            # Any other repeated/unresolved issue → general escalation
            reason = "Repeated or unresolved issue detected"
            logger.info("Pre-flight: repeated issue | conversation=%s", conversation_id)
            return AIResponse(
                response=_pick_variant(_GENERAL_ESCALATION_VARIANTS, conversation_history),
                intent="complaint",
                confidence=0.9,
                should_escalate=True,
                escalation_reason=reason,
            )

        if intent == "account_issue":
            # First-time account/login issue → give troubleshooting steps
            logger.info("Pre-flight: account first-time | conversation=%s", conversation_id)
            return AIResponse(
                response=_pick_variant(_ACCOUNT_TROUBLESHOOT_VARIANTS, conversation_history),
                intent="account",
                confidence=0.85,
                should_escalate=False,
            )

        ctx = AgentContext(db=db, user_id=user_id, conversation_id=conversation_id)
        executor = ToolExecutor()
        client = get_openai_client()

        messages = self._build_initial_messages(conversation_history, user_message)

        try:
            for iteration in range(self.MAX_ITERATIONS):
                ctx.iterations = iteration + 1
                logger.debug("Agent iteration %d/%d", iteration + 1, self.MAX_ITERATIONS)

                response = await client.chat.completions.create(
                    model=settings.OPENAI_MODEL,
                    messages=messages,  # type: ignore[arg-type]
                    tools=TOOL_DEFINITIONS,  # type: ignore[arg-type]
                    tool_choice="required",  # force tool use every turn
                    temperature=0.3,
                    max_tokens=1000,
                )

                msg = response.choices[0].message

                # No tool calls — model tried to respond directly.
                # This should not happen with tool_choice="required", but handle
                # defensively in case the API behaves unexpectedly.
                if not msg.tool_calls:
                    logger.warning(
                        "Agent produced no tool calls on iteration %d", iteration
                    )
                    if msg.content:
                        ctx.final_response = msg.content
                    break

                # Append assistant message with its tool calls to the history
                messages.append(
                    {
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
                    }
                )

                # Execute each tool call in sequence
                for tool_call in msg.tool_calls:
                    tool_name = tool_call.function.name
                    args = _json.loads(tool_call.function.arguments)

                    logger.info(
                        "Agent calling tool: %s | args=%s",
                        tool_name,
                        list(args.keys()),
                    )

                    result = await executor.execute(tool_name, args, ctx)

                    # Feed tool result back into the conversation
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result,
                        }
                    )

                    # send_response sets ctx.final_response — terminate loop
                    if tool_name == "send_response" and ctx.final_response:
                        break

                if ctx.final_response:
                    break

            # ---------------------------------------------------------------
            # Build AIResponse from accumulated context
            # ---------------------------------------------------------------
            if not ctx.final_response:
                logger.warning(
                    "Agent loop ended after %d iterations without send_response — "
                    "using fallback",
                    self.MAX_ITERATIONS,
                )
                return _build_fallback_response(user_message)

            return AIResponse(
                response=ctx.final_response,
                intent=ctx.intent,
                confidence=ctx.confidence,
                should_escalate=ctx.should_escalate,
                escalation_reason=ctx.escalation_reason,
                tools_called=ctx.tools_called,
                iterations=ctx.iterations,
                kb_articles_found=ctx.kb_articles_found,
                ticket_created=ctx.ticket_created,
            )

        except Exception as exc:  # noqa: BLE001
            logger.error("SupportAgent.run() failed: %s", exc, exc_info=True)
            return _build_fallback_response(user_message)

    def _build_initial_messages(
        self,
        conversation_history: list[dict],
        user_message: str,
    ) -> list[dict]:
        """Build the initial messages array for the agent.

        Includes the system prompt, up to the last 6 history entries (to stay
        within context window limits), and the new user message.

        Args:
            conversation_history: Prior messages in ``{sender_type, content}`` format.
            user_message: The latest customer message.

        Returns:
            List of message dicts ready for the OpenAI chat completions API.
        """
        messages: list[dict] = [{"role": "system", "content": AGENT_SYSTEM_PROMPT}]

        for entry in conversation_history[-6:]:  # last 6 turns for context window
            sender = entry.get("sender_type", "user")
            content = entry.get("content", "")

            if sender == "user":
                messages.append({"role": "user", "content": content})
            elif sender in ("ai", "agent"):
                # Strip the JSON wrapper used by the old AIService so that
                # historical assistant messages are human-readable text.
                try:
                    parsed = _json.loads(content)
                    content = parsed.get("response", content)
                except Exception:  # noqa: BLE001
                    pass
                messages.append({"role": "assistant", "content": content})

        messages.append({"role": "user", "content": user_message})
        return messages


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

support_agent = SupportAgent()
