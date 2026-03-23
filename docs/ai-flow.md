# AI Flow — Tool-Based Agent Architecture

> Describes how SupportPilot AI processes inbound support messages using a structured, tool-calling agent loop.

---

## Overview

SupportPilot AI uses a **tool-based agentic approach** rather than a single prompt-response call. The agent runs a multi-step reasoning loop using OpenAI's function calling API, invoking a defined set of tools in a strict order before delivering a response.

This architecture provides:
- **Structured workflow** — every interaction follows the same steps (history → KB → ticket → respond)
- **Auditability** — every tool call is logged with its arguments and result
- **Extensibility** — adding new capabilities = adding a new tool, not rewriting the agent
- **Reliability** — fallback response on any failure, always escalates on error

---

## Agent Entry Points

The agent is invoked from two places:

| Caller | File | When |
|---|---|---|
| `MessageService.send_message()` | `app/services/message.py` | Customer sends a chat message |
| `SupportService._submit_inline()` | `app/services/support.py` | Web support form submitted |
| `MessageProcessorWorker._process_*()` | `workers/message_processor.py` | Kafka mode: worker consumes event |

All three call `support_agent.run(db, user_id, conversation_id, user_message, conversation_history)` and receive back an `AIResponse`.

---

## Agent Tool Workflow

```
Customer message received
         │
         ▼
┌─────────────────────────────────┐
│  STEP 1: get_customer_history   │  ← ALWAYS first
│  Fetch past tickets &           │
│  conversations for this user    │
└──────────────┬──────────────────┘
               │ history context
               ▼
┌─────────────────────────────────┐
│  STEP 2: search_knowledge_base  │  ← ALWAYS second
│  Keyword search for relevant    │
│  articles and FAQs              │
└──────────────┬──────────────────┘
               │ kb context
               ▼
┌─────────────────────────────────┐
│  STEP 3: create_ticket          │  ← ALWAYS third
│  Create support ticket with     │
│  inferred category and priority │
└──────────────┬──────────────────┘
               │
         ┌─────┴─────┐
         │           │
   escalation?      no
   needed?          │
         │           │
         ▼           │
┌────────────────┐   │
│  STEP 4:       │   │
│  escalate_     │   │
│  to_human      │   │
│  (conditional) │   │
└────────┬───────┘   │
         │           │
         └─────┬─────┘
               │
               ▼
┌─────────────────────────────────┐
│  STEP 5: send_response          │  ← ALWAYS last — terminates loop
│  Final reply with intent and    │
│  confidence classification      │
└──────────────┬──────────────────┘
               │
               ▼
         AIResponse returned
         (response, intent, confidence,
          should_escalate, escalation_reason)
```

---

## Tool Definitions

### `get_customer_history`
- **When:** Always first
- **What:** Fetches the last 5 tickets and 3 conversations for the user
- **Returns:** Formatted history string injected back to the model
- **DB access:** `TicketRepository.get_by_user()`, `ConversationRepository.get_by_user()`

### `search_knowledge_base`
- **When:** Always second
- **What:** Keyword search across KB title, content, and tags using SQL `ilike`
- **Returns:** Top 3 matching article excerpts (500 chars each)
- **DB access:** `KnowledgeBaseRepository.search(query, limit=3)`
- **Phase 2:** Will be replaced with vector similarity search via pgvector

### `create_ticket`
- **When:** Always third (unless ticket already exists for this conversation)
- **What:** Creates a support ticket with agent-inferred category and priority
- **Inputs:** title, description, category (6 options), priority (4 levels)
- **DB access:** `TicketRepository.create()`
- **Effect:** Sets `ctx.ticket_id`, `ctx.ticket_created = True`

### `escalate_to_human`
- **When:** Conditional — triggered when agent detects:
  - Billing disputes or refund demands
  - Legal language or compliance concerns
  - Explicit "I want to speak to a human" request
  - Account security concerns
  - High frustration indicators
  - Repeated unresolved issue
- **What:** Updates conversation status to `escalated`
- **DB access:** `ConversationRepository.update(id, {"status": "escalated"})`
- **Effect:** Sets `ctx.should_escalate = True`, `ctx.escalation_reason`

### `send_response`
- **When:** Always last — calling this terminates the agent loop
- **What:** Stores the final response text + intent + confidence in `AgentContext`
- **No DB access** — response is stored by the calling service after the loop
- **Effect:** Sets `ctx.final_response`, `ctx.intent`, `ctx.confidence`

---

## Agent Loop

```python
for iteration in range(MAX_ITERATIONS=8):
    response = await openai.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=messages,
        tools=TOOL_DEFINITIONS,
        tool_choice="required",   # model MUST call a tool each turn
        temperature=0.3,
    )

    for tool_call in response.choices[0].message.tool_calls:
        result = await executor.execute(tool_call.name, tool_call.args, ctx)
        messages.append(tool result)

        if tool_call.name == "send_response" and ctx.final_response:
            break  # Loop terminates here

    if ctx.final_response:
        break
```

- `tool_choice="required"` forces the model to always call a tool (no direct text responses)
- Maximum 8 iterations prevents infinite loops
- If the loop ends without `send_response`, `_FALLBACK_RESPONSE` is returned with `should_escalate=True`

---

## AgentContext

State accumulated during a single agent run:

```python
@dataclass
class AgentContext:
    db: AsyncSession
    user_id: str
    conversation_id: str
    # Accumulated state
    ticket_id: str | None = None
    should_escalate: bool = False
    escalation_reason: str | None = None
    final_response: str | None = None
    intent: str = "general"
    confidence: float = 0.7
    # Progress flags
    history_loaded: bool = False
    kb_searched: bool = False
    ticket_created: bool = False
```

---

## Intent Categories

| Intent | Description | Typical trigger phrases |
|---|---|---|
| `general` | General enquiry or information request | "How does X work?" |
| `technical` | Bug reports, errors, configuration | "The app crashes when..." |
| `billing` | Payments, invoices, subscriptions, refunds | "I was charged..." |
| `account` | Login, password, profile management | "I can't log in..." |
| `complaint` | Dissatisfaction, negative feedback | "This is unacceptable..." |
| `feature_request` | Suggestions for new features | "Can you add..." |
| `urgent` | Time-critical, production-down | "Our system is down..." |

---

## AIResponse Contract

All callers receive the same `AIResponse` dataclass regardless of which execution path ran:

```python
@dataclass
class AIResponse:
    response: str          # The text to show the customer
    intent: str            # Classified intent category
    confidence: float      # 0.0–1.0 classification confidence
    should_escalate: bool  # Whether human takeover was flagged
    escalation_reason: str | None  # Why escalation was flagged
```

---

## Metrics Collection

After every agent run, `AgentMetrics` is recorded:

```
conversation_id, user_id, intent_detected, confidence_score,
tools_called (list), iterations, response_time_ms, model_used,
was_escalated, ticket_created, kb_articles_found
```

Stored in `agent_metrics` table. Powers the admin analytics dashboard.

---

## Error Handling

| Failure scenario | Behaviour |
|---|---|
| OpenAI API error | `_FALLBACK_RESPONSE` returned, `should_escalate=True` |
| Agent loop exhausted (8 iterations) | `_FALLBACK_RESPONSE`, logged as warning |
| Tool execution error | Error string returned to model, loop continues |
| DB error in tool | Exception propagates, caught in `SupportAgent.run()`, fallback |
| Metrics recording fails | Warning logged, response unaffected |

---

## Phase 2: RAG Knowledge Base

When pgvector is added, `search_knowledge_base` will switch from keyword to vector similarity:

```python
# Phase 1 (now): SQL ilike keyword match
results = await kb_repo.search(query, limit=3)

# Phase 2 (planned): vector similarity via pgvector
embedding = await openai.embeddings.create(input=query, model="text-embedding-3-small")
results = await kb_repo.search_by_vector(embedding.data[0].embedding, limit=3)
```

No changes to the agent loop or other tools — only `search_knowledge_base` implementation changes.
