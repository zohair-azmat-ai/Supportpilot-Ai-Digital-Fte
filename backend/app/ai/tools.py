"""
AI agent tool definitions and implementations.

Tools follow OpenAI's function calling format. Each tool has:
- A JSON schema definition (for the OpenAI API)
- An async Python implementation (called when the model invokes the tool)

Tool execution order (enforced by agent system prompt):
  1. get_customer_history   — ALWAYS first
  2. search_knowledge_base  — ALWAYS second
  3. create_ticket          — ALWAYS third (unless ticket already exists)
  4. escalate_to_human      — ONLY if escalation needed
  5. send_response          — ALWAYS last (terminates the agent loop)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from app.schemas.ai_decision import SupportDecision


# ---------------------------------------------------------------------------
# OpenAI-compatible tool schema definitions
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "get_customer_history",
            "description": (
                "Retrieve the customer's recent support history including past tickets "
                "and conversations. MUST be called first before any other tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "The customer's user ID",
                    }
                },
                "required": ["user_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "Search the knowledge base for articles relevant to the customer's "
                "issue. MUST be called after get_customer_history."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Keywords or phrases describing the customer's issue",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": (
                "Create a support ticket for this customer interaction. MUST be called "
                "before send_response unless a ticket already exists for this conversation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "technical",
                            "billing",
                            "account",
                            "general",
                            "complaint",
                            "feature_request",
                        ],
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "urgent"],
                    },
                },
                "required": ["title", "description", "category", "priority"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "escalate_to_human",
            "description": (
                "Flag this conversation for human agent takeover. Call when: billing "
                "disputes, legal mentions, explicit human request, security concerns, "
                "high frustration, or unresolvable issues."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why escalation is needed",
                    },
                    "urgency": {
                        "type": "string",
                        "enum": ["normal", "urgent"],
                    },
                },
                "required": ["reason", "urgency"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_response",
            "description": (
                "Send the final response to the customer. MUST be the last tool called. "
                "This terminates the agent loop."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "The response message to send to the customer",
                    },
                    "intent": {
                        "type": "string",
                        "enum": [
                            "general",
                            "technical",
                            "billing",
                            "account",
                            "complaint",
                            "feature_request",
                            "urgent",
                        ],
                    },
                    "confidence": {
                        "type": "number",
                        "description": "0.0-1.0 confidence in intent classification",
                    },
                },
                "required": ["message", "intent", "confidence"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# Agent context — mutable state accumulated during one agent run
# ---------------------------------------------------------------------------


class AgentContext:
    """Context passed to tool executors during an agent run."""

    def __init__(self, db: Any, user_id: str, conversation_id: str) -> None:
        self.db = db
        self.user_id = user_id
        self.conversation_id = conversation_id
        # Mutable state accumulated during the run
        self.ticket_id: str | None = None
        self.should_escalate: bool = False
        self.escalation_reason: str | None = None
        self.final_response: str | None = None
        self.intent: str = "general"
        self.confidence: float = 0.7
        self.history_loaded: bool = False
        self.kb_searched: bool = False
        self.ticket_created: bool = False
        # Analytics — populated as tools are called
        self.tools_called: list[str] = []
        self.iterations: int = 0
        self.kb_articles_found: int = 0
        # Pre-determined decision from SupportDecisionEngine (injected by SupportAgent)
        # When set, send_response uses this reply/intent/confidence instead of the
        # model-generated message, ensuring the decision engine is the source of truth.
        self.predecided: Optional["SupportDecision"] = None
        # Similar issue signals (populated from ConversationContext by SupportAgent)
        self.similar_issue_found: bool = False
        self.unresolved_similar_ticket_ids: list[str] = []


# ---------------------------------------------------------------------------
# Tool executor — dispatches tool calls and updates context
# ---------------------------------------------------------------------------


class ToolExecutor:
    """Executes agent tool calls and updates AgentContext."""

    async def execute(
        self,
        tool_name: str,
        args: dict[str, Any],
        ctx: AgentContext,
    ) -> str:
        """Execute a tool and return its string result (fed back to model)."""
        handlers = {
            "get_customer_history": self._get_customer_history,
            "search_knowledge_base": self._search_knowledge_base,
            "create_ticket": self._create_ticket,
            "escalate_to_human": self._escalate_to_human,
            "send_response": self._send_response,
        }
        handler = handlers.get(tool_name)
        if not handler:
            return f"Error: unknown tool '{tool_name}'"
        # Track tool invocations for metrics
        ctx.tools_called.append(tool_name)
        return await handler(args, ctx)

    # ------------------------------------------------------------------
    # Individual tool implementations
    # ------------------------------------------------------------------

    async def _get_customer_history(self, args: dict, ctx: AgentContext) -> str:
        """Fetch customer's recent tickets, conversations, and cross-channel identity."""
        from app.repositories.conversation import ConversationRepository
        from app.repositories.customer import CustomerRepository
        from app.repositories.ticket import TicketRepository

        ticket_repo = TicketRepository(ctx.db)
        conv_repo = ConversationRepository(ctx.db)
        customer_repo = CustomerRepository(ctx.db)

        tickets = await ticket_repo.get_by_user(ctx.user_id, skip=0, limit=5)
        conversations = await conv_repo.get_by_user(ctx.user_id, skip=0, limit=5)
        customer = await customer_repo.get_by_user_id(ctx.user_id)

        ctx.history_loaded = True

        history_lines: list[str] = []

        # Cross-channel customer profile
        if customer:
            history_lines.append(
                f"Customer profile: {customer.name}"
                + (f" | company={customer.company}" if customer.company else "")
                + (f" | plan={customer.plan}" if customer.plan else "")
            )
            if customer.identifiers:
                channels = ", ".join(
                    f"{ci.channel}:{ci.value}" for ci in customer.identifiers
                )
                history_lines.append(f"Cross-channel identities: {channels}")

        if not tickets and not conversations:
            history_lines.append(
                "No prior support history found. This appears to be the customer's first contact."
            )
            return "\n".join(history_lines) if history_lines else (
                "No prior support history found. This appears to be the customer's first contact."
            )

        if tickets:
            history_lines.append(f"\nSupport tickets ({len(tickets)}):")
            for t in tickets:
                history_lines.append(
                    f"  • [{t.id[:8]}] {t.title} | status={t.status} "
                    f"| priority={t.priority} | category={t.category}"
                )

        if conversations:
            history_lines.append(f"\nConversations ({len(conversations)}):")
            for c in conversations:
                history_lines.append(
                    f"  • [{c.id[:8]}] channel={c.channel} | status={c.status}"
                    + (f" | subject={c.subject}" if c.subject else "")
                )

        return "\n".join(history_lines)

    async def _search_knowledge_base(self, args: dict, ctx: AgentContext) -> str:
        """Search knowledge base with keyword + confidence scoring."""
        from app.repositories.knowledge_base import KnowledgeBaseRepository

        query = args.get("query", "")
        kb_repo = KnowledgeBaseRepository(ctx.db)
        results = await kb_repo.search_with_scores(query, limit=4)

        ctx.kb_searched = True
        ctx.kb_articles_found = len(results)

        if not results:
            return (
                f"No knowledge base articles found for query: '{query}'. "
                "Respond from general knowledge and best judgement."
            )

        lines = [f"Knowledge base results for '{query}' ({len(results)} articles found):"]
        for item, score in results:
            lines.append(
                f"\n## {item.title}  [relevance: {score:.0%}]\n"
                f"Category: {item.category}\n"
                f"{item.content[:600]}"
                + ("..." if len(item.content) > 600 else "")
            )

        return "\n".join(lines)

    async def _create_ticket(self, args: dict, ctx: AgentContext) -> str:
        """Create a support ticket for this interaction.

        Checks for an existing ticket on this conversation first to avoid
        creating duplicates when the agent is called across multiple turns.
        """
        from app.repositories.ticket import TicketRepository

        ticket_repo = TicketRepository(ctx.db)

        # -- Duplicate guard: reuse existing ticket for this conversation --
        existing = await ticket_repo.get_by_conversation(ctx.conversation_id)
        if existing:
            open_ticket = next(
                (t for t in existing if t.status in ("open", "in_progress")),
                existing[0],
            )
            ctx.ticket_id = open_ticket.id
            ctx.ticket_created = False  # not created, just reused
            return (
                f"Ticket already exists for this conversation: "
                f"ID={open_ticket.id[:8].upper()} "
                f"| title='{open_ticket.title}' | status={open_ticket.status} "
                f"| priority={open_ticket.priority}"
            )

        # -- Create new ticket enriched with AI signals --
        ticket_data: dict = {
            "user_id": ctx.user_id,
            "conversation_id": ctx.conversation_id,
            "title": args["title"],
            "description": args["description"],
            "category": args["category"],
            "priority": args["priority"],
        }
        if ctx.predecided is not None:
            ticket_data["sentiment"] = ctx.predecided.sentiment
            ticket_data["urgency"] = ctx.predecided.urgency
            if ctx.predecided.escalate and ctx.predecided.escalation_reason:
                ticket_data["escalation_reason"] = ctx.predecided.escalation_reason

        ticket = await ticket_repo.create(ticket_data)

        ctx.ticket_id = ticket.id
        ctx.ticket_created = True

        result = (
            f"Ticket created: ID={ticket.id[:8].upper()} "
            f"| title='{ticket.title}' | priority={ticket.priority}"
        )

        # Inform the LLM if similar unresolved tickets exist for this user
        if ctx.unresolved_similar_ticket_ids:
            ids = ", ".join(t[:8].upper() for t in ctx.unresolved_similar_ticket_ids[:3])
            result += (
                f"\nNote: User has {len(ctx.unresolved_similar_ticket_ids)} similar "
                f"unresolved ticket(s) from previous sessions: {ids}. "
                "Consider referencing these in your response."
            )

        return result

    async def _escalate_to_human(self, args: dict, ctx: AgentContext) -> str:
        """Flag conversation for human escalation."""
        from app.repositories.conversation import ConversationRepository

        conv_repo = ConversationRepository(ctx.db)
        await conv_repo.update(ctx.conversation_id, {"status": "escalated"})

        ctx.should_escalate = True
        ctx.escalation_reason = args.get("reason", "Escalated by AI agent")

        urgency = args.get("urgency", "normal")
        return (
            f"Escalation flagged | reason='{ctx.escalation_reason}' | urgency={urgency}. "
            "Conversation status set to 'escalated'."
        )

    async def _send_response(self, args: dict, ctx: AgentContext) -> str:
        """Set the final response — terminates the agent loop.

        When a pre-determined decision exists (injected by SupportDecisionEngine),
        the decision's reply is used as the response text instead of the model-
        generated message.  Intent and confidence always reflect the decision engine.
        """
        if ctx.predecided is not None:
            # Decision engine is the source of truth for the reply
            ctx.final_response = ctx.predecided.reply
            ctx.intent = ctx.predecided.intent
            ctx.confidence = ctx.predecided.confidence
        else:
            ctx.final_response = args["message"]
            ctx.intent = args.get("intent", "general")
            ctx.confidence = float(args.get("confidence", 0.7))

        return (
            f"Response queued for delivery. "
            f"intent={ctx.intent} confidence={ctx.confidence:.2f}"
        )
