# Discovery Log

> Ongoing log of development decisions, technical learnings, and architectural trade-offs made during the SupportPilot AI build.
> Each entry should include a date, context, decision made, and the reasoning behind it.

---

## Format

```
### [YYYY-MM-DD] — <Short title>
**Context:** What problem or question triggered this decision.
**Decision:** What was decided.
**Reasoning:** Why this approach was chosen over alternatives.
**Impact:** What this affects going forward.
```

---

## Entries

### [2026-03-23] — Monorepo structure chosen over separate repos

**Context:** Deciding whether to use a monorepo or split frontend/backend into separate repositories.

**Decision:** Single monorepo with `frontend/` and `backend/` top-level directories.

**Reasoning:** Given the project is a portfolio showcase with tight frontend/backend coordination, a monorepo simplifies local development, reduces context-switching, and makes the codebase easier for reviewers to understand in one shot. Shared types and docs live alongside the code.

**Impact:** All future contributors work in one repo. If the project scales to a team, splitting repos can be revisited.

---

### [2026-03-23] — Async SQLAlchemy selected over sync ORM

**Context:** Choosing between synchronous and asynchronous SQLAlchemy for the FastAPI backend.

**Decision:** Use `sqlalchemy[asyncio]` with `asyncpg` driver throughout.

**Reasoning:** FastAPI is built around async. Using a synchronous ORM would block the event loop on every DB query, negating FastAPI's concurrency advantages. Async SQLAlchemy is the production-standard choice for async Python backends.

**Impact:** All repository methods and service calls are `async def`. Alembic requires a special async `env.py` setup (already implemented).

---

### [2026-03-23] — gpt-4o-mini chosen as default AI model

**Context:** Selecting which OpenAI model to use for support response generation.

**Decision:** Default to `gpt-4o-mini`. Make the model configurable via `OPENAI_MODEL` env variable.

**Reasoning:** gpt-4o-mini provides a strong quality/cost ratio for customer support tasks. Response times are acceptable for chat UX. For demos and portfolio purposes, the cost is negligible. The `OPENAI_MODEL` env var allows upgrading to `gpt-4o` or `gpt-4-turbo` without code changes.

**Impact:** AI service reads model from settings. Production deployments can override without redeployment.

---

### [2026-03-23] — JSON mode for structured AI output

**Context:** Deciding how to extract structured fields (intent, confidence, escalation flag) from the AI response.

**Decision:** Use OpenAI's `response_format={"type": "json_object"}` combined with a system prompt that specifies the exact JSON schema expected.

**Reasoning:** Alternatives considered: (1) regex extraction from free text — brittle; (2) function/tool calling — more overhead, overkill for this shape; (3) JSON mode — clean, reliable, supported natively. The system prompt defines the schema, JSON mode enforces it.

**Impact:** `AIService._parse_response()` assumes JSON output. A fallback parser handles any malformed output gracefully.

---

### [2026-03-23] — UUID primary keys over auto-increment integers

**Context:** Choosing primary key strategy for all database entities.

**Decision:** Use UUID v4 (`uuid.uuid4`) as the default primary key type, stored as `String(36)`.

**Reasoning:** UUIDs are collision-resistant across distributed systems, don't expose record counts/order to API consumers, and are the de-facto standard in SaaS backends. `String(36)` is used (over native UUID column type) for maximum compatibility across Postgres hosts (Neon, Railway, local).

**Impact:** All IDs in API responses and frontend types are `string`, not `number`.

---

### [2026-03-23] — Support form creates a guest user on first submission

**Context:** The web support form (`POST /support/submit`) is public — no login required. A decision was needed on how to associate the submission with a user record.

**Decision:** The support service looks up a user by email. If none exists, it creates a new `customer` role user with a random password hash. The same user record is reused on subsequent submissions from the same email.

**Reasoning:** This allows anonymous support submissions while still maintaining relational integrity (tickets and conversations have a `user_id` FK). It also means returning users can optionally create an account later and will already have history.

**Impact:** The `SupportService` handles user resolution before creating conversations/tickets. Guest users have no usable password until they go through the signup flow.

---

### [2026-03-23] — Next.js App Router (not Pages Router)

**Context:** Choosing which Next.js routing paradigm to use.

**Decision:** App Router with route groups: `(auth)`, `(customer)`, `(admin)`.

**Reasoning:** App Router is the current Next.js standard (v14+). Route groups allow layout sharing without affecting URL paths, which is exactly what dashboard-style apps need. Server Components are available for future optimization if needed.

**Impact:** All pages use `'use client'` where interactivity is needed. Layouts provide nested UI shells (sidebar, header) per user role.

---

### [2026-03-23] — Channel adapter pattern chosen over inline channel logic

**Context:** Gmail and WhatsApp integrations need to be architectured cleanly even before credentials are available. The risk was either (a) coupling channel-specific logic directly into SupportService, or (b) over-engineering with Kafka upfront.

**Decision:** Introduce a `BaseChannelAdapter` abstract class in `backend/app/channels/`. Each channel (web, email, WhatsApp) implements `parse_inbound()` and `send_response()`. SupportService only receives a normalised `InboundMessage` — it never sees raw channel payloads.

**Reasoning:** The adapter pattern isolates channel-specific code completely, makes adding new channels trivial (one new file, no service changes), and is the natural insertion point for a Kafka queue in Phase 3 (workers consume from topics and call the same adapters). It also lets us scaffold Gmail and WhatsApp now with `NotImplementedError` guards and activate them later by adding credentials — without any architectural rework.

**Impact:** `backend/app/channels/` is a first-class layer in the architecture. All documentation and the README now reflect it. Kafka/Kubernetes are documented in `docs/specs/scaling-architecture.md` as Phase 3 — not added to the MVP codebase.

---

### [2026-03-23] — Kafka and Kubernetes deferred to Phase 3

**Context:** The Hackathon 5 specification referenced Kafka and Kubernetes as part of the architecture. The question was whether to add them to the MVP.

**Decision:** Document them as Phase 3 in `docs/specs/scaling-architecture.md`. Do not add them to the codebase.

**Reasoning:** Adding Kafka to the MVP adds significant complexity (Docker Compose config, consumer setup, serialisation) with no user-visible benefit at current scale. The adapter pattern already provides the clean insertion point — switching from inline calls to Kafka consumers requires no service layer changes. Kafka adds real value at high message volume with multiple channels running concurrently. That's not now.

**Impact:** The scaling architecture doc exists so future engineers (or a future version of this project) can execute the migration without redesigning the service layer.

---

## Pending Decisions

| Topic | Status | Notes |
|---|---|---|
| Real-time updates (WebSockets vs polling) | Pending | Currently uses request/response. Chat UX could benefit from WS for streaming. |
| Email channel integration | Pending | Architecture is ready; Gmail OAuth + webhook listener not yet wired. |
| WhatsApp channel integration | Pending | Twilio sandbox credentials needed; adapter stub exists. |
| RAG knowledge base | Pending | Pinecone/pgvector integration planned for Phase 2. |
| Rate limiting | Pending | No rate limiting on `/support/submit` yet — needed before public deployment. |
| Refresh token strategy | Pending | Currently using long-lived access tokens (7 days). Refresh token rotation is a security improvement. |
