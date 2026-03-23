# SupportPilot AI — Architecture Documentation

## Table of Contents

1. [System Overview](#system-overview)
2. [Component Breakdown](#component-breakdown)
3. [Data Flow](#data-flow)
4. [Layer Descriptions](#layer-descriptions)
5. [Authentication Flow](#authentication-flow)
6. [AI Processing Pipeline](#ai-processing-pipeline)
7. [Multi-Channel Architecture](#multi-channel-architecture)
8. [Scalability Considerations](#scalability-considerations)

---

## System Overview

```
                                   ┌──────────────────────────────┐
                                   │        EXTERNAL CLIENTS       │
                                   │  Browser  │  Email  │ WhatsApp│
                                   └─────┬─────┴────┬────┴────┬────┘
                                         │          │         │
                              HTTPS/REST │    SMTP  │  Twilio │
                                         │          │         │
┌────────────────────────────────────────▼──────────▼─────────▼────────────────┐
│                            FRONTEND — Vercel (CDN Edge)                       │
│                                                                               │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐    │
│   │  Auth Pages │   │  Chat Pages │   │Ticket Pages │   │ Admin Pages │    │
│   │  /login     │   │  /chat      │   │  /tickets   │   │  /admin/*   │    │
│   │  /signup    │   │  /chat/[id] │   │  /support   │   │             │    │
│   └─────────────┘   └─────────────┘   └─────────────┘   └─────────────┘    │
│                                                                               │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │   Shared: Components │ Hooks │ Context │ Lib (API Client) │ Types   │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────┬───────────────────────────────────────┘
                                        │ HTTPS REST API
┌───────────────────────────────────────▼───────────────────────────────────────┐
│                           BACKEND — Railway                                   │
│                                                                               │
│   ┌──────────────────────────────────────────────────────────────────────┐   │
│   │                        FastAPI Application                           │   │
│   │                                                                      │   │
│   │  ROUTE LAYER (/api/v1/*)                                             │   │
│   │  ┌──────┐ ┌────────┐ ┌───────┐ ┌───────┐ ┌─────────┐ ┌────────┐   │   │
│   │  │ auth │ │ conv.  │ │  msg  │ │ticket │ │ support │ │ admin  │   │   │
│   │  └──────┘ └────────┘ └───────┘ └───────┘ └─────────┘ └────────┘   │   │
│   │                                                                      │   │
│   │  SERVICE LAYER                                                       │   │
│   │  ┌────────────┐ ┌──────────────────┐ ┌─────────────┐               │   │
│   │  │AuthService │ │ConversationSvc   │ │TicketService│               │   │
│   │  └────────────┘ └──────────────────┘ └─────────────┘               │   │
│   │                                                                      │   │
│   │  REPOSITORY LAYER                                                    │   │
│   │  ┌──────────┐ ┌────────────────┐ ┌────────────┐ ┌───────────┐     │   │
│   │  │ UserRepo │ │ConversationRepo│ │MessageRepo │ │TicketRepo │     │   │
│   │  └──────────┘ └────────────────┘ └────────────┘ └───────────┘     │   │
│   └──────────────────────────────────────────────────────────────────────┘   │
│                           │                         │                         │
└───────────────────────────┼─────────────────────────┼─────────────────────────┘
                            │                         │
          ┌─────────────────▼──────┐     ┌────────────▼────────┐
          │  PostgreSQL — Neon      │     │    OpenAI API        │
          │  (Managed Serverless)   │     │  GPT-4o-mini         │
          │                         │     │  Intent + Response   │
          │  users                  │     │                      │
          │  conversations          │     └──────────────────────┘
          │  messages               │
          │  tickets                │
          └─────────────────────────┘
```

---

## Component Breakdown

### Frontend Components

| Component Group | Location | Responsibility |
|---|---|---|
| Auth Pages | `app/(auth)/` | Login/signup forms, credential validation, JWT storage |
| Customer Pages | `app/(customer)/` | Chat, tickets, support form, user dashboard |
| Admin Pages | `app/(admin)/admin/` | Dashboard stats, ticket/conversation/user management |
| UI Primitives | `components/ui/` | Buttons, inputs, modals, badges, spinners |
| Layout | `components/layout/` | Sidebars, navigation, page wrappers |
| Chat Components | `components/chat/` | Message bubbles, conversation list, input bar |
| Ticket Components | `components/tickets/` | Ticket cards, status badges, filters |
| API Client | `lib/` | Axios instance with auth interceptors |
| Custom Hooks | `hooks/` | `useAuth`, `useConversation`, `useTickets`, etc. |
| Context | `context/` | `AuthContext` — global auth state |
| Types | `types/` | Shared TypeScript interface definitions |

### Backend Components

| Component | Location | Responsibility |
|---|---|---|
| FastAPI App | `app/main.py` | App instantiation, CORS, router mounting |
| Config | `app/core/config.py` | Pydantic Settings loading from `.env` |
| Database | `app/core/database.py` | Async SQLAlchemy engine, session factory |
| Security | `app/core/security.py` | JWT encode/decode, bcrypt hash/verify |
| Dependencies | `app/core/deps.py` | `get_current_user`, `require_admin` FastAPI deps |
| ORM Models | `app/models/` | SQLAlchemy table definitions |
| Pydantic Schemas | `app/schemas/` | Request/response validation schemas |
| Routes | `app/api/v1/routes/` | HTTP endpoint handlers |
| Services | `app/services/` | Business logic orchestration |
| Repositories | `app/repositories/` | All database query abstractions |
| AI Service | `app/ai/ai_service.py` | OpenAI API integration, intent classification |
| Utils | `app/utils/` | Shared helpers |

---

## Data Flow

### Customer Sends a Chat Message

```
Browser (React)
    │
    │  POST /api/v1/conversations/{id}/messages
    │  Body: { "content": "My order hasn't arrived" }
    │  Header: Authorization: Bearer <JWT>
    ▼
FastAPI Route Handler (messages.py)
    │  1. Validate JWT via deps.get_current_user
    │  2. Validate request body via Pydantic schema
    ▼
ConversationService
    │  1. Verify conversation ownership
    │  2. Persist customer message via MessageRepository
    │  3. Build conversation history (last N messages)
    │  4. Call AIService.generate_response(history, content)
    ▼
AIService
    │  1. Classify intent via GPT-4o-mini
    │  2. Determine escalation need
    │  3. Generate support response
    │  Returns: { response, intent, confidence, should_escalate }
    ▼
ConversationService (continued)
    │  1. Persist AI response message with intent + confidence
    │  2. If escalation: update conversation status, create ticket
    │  3. Return both messages to route handler
    ▼
FastAPI Route Handler
    │  Serialize response via Pydantic schema
    ▼
Browser (React)
    Renders AI response in chat UI
```

### Customer Submits Web Support Form

```
Browser → POST /api/v1/support/submit
    │  { name, email, subject, description, category }
    ▼
SupportService
    ├── 1. Find or create user account (by email)
    ├── 2. Create conversation (channel: "web_form")
    ├── 3. Persist customer message
    ├── 4. Call AIService → get initial response
    ├── 5. Persist AI response message
    └── 6. Create ticket (linked to conversation + user)
    ▼
Response: { conversation_id, ticket_id, ai_response }
```

---

## Layer Descriptions

### Frontend Layer (Next.js 14 App Router)

The frontend is built on Next.js 14 using the App Router paradigm. Route groups `(auth)`, `(customer)`, and `(admin)` provide layout isolation without affecting URL paths. Server Components handle initial data needs where applicable; Client Components handle interactivity, forms, and real-time updates.

State management is intentionally lightweight: `AuthContext` holds the global session state (user object + JWT). All other state is local to pages or managed via custom hooks that wrap Axios API calls.

Auth tokens are stored in `localStorage` and attached to every outbound request via an Axios request interceptor. A 401 response interceptor redirects to `/login`.

### API Layer (FastAPI Routes)

Routes are the HTTP boundary. Their only concerns are:
1. Declaring the HTTP method, path, and response model
2. Extracting dependencies (`current_user`, `db` session) via FastAPI's `Depends`
3. Delegating to a service function
4. Returning the serialized Pydantic response

Routes contain no business logic. They are thin adapters between HTTP and the service layer.

### Service Layer

Services contain all business logic. They orchestrate across multiple repositories and external services (OpenAI). Services are injected with an async SQLAlchemy `AsyncSession` and call repositories as needed.

Examples of service responsibilities:
- Verifying a user owns a resource before accessing it
- Deciding whether to create a ticket on escalation
- Calling AIService and deciding what to do with the response

### Repository Layer

Repositories are the only code that talks to the database. They accept an `AsyncSession` and return ORM model instances or primitive values. No SQL outside of repositories.

This isolation means the database layer can be swapped or mocked for testing without touching service or route code.

### AI Layer

`AIService` is a stateless async class wrapping the OpenAI client. It receives message history and the current message content. It returns structured data (intent label, confidence float, response text, escalation boolean). All prompt engineering lives here. See [ai-flow.md](ai-flow.md) for full details.

### Database Layer (PostgreSQL + SQLAlchemy)

The database is accessed exclusively through async SQLAlchemy with asyncpg as the driver. The async engine uses a connection pool appropriate for the deployment environment. Alembic manages all schema migrations; no manual SQL DDL is run in production.

---

## Authentication Flow

```
1. SIGNUP
   Client → POST /auth/signup { name, email, password }
   Server:
     - Check email uniqueness (UserRepository)
     - Hash password with bcrypt (passlib)
     - Create user record with role="customer"
     - Generate JWT (python-jose, HS256)
     - Return { access_token, token_type, user }

2. LOGIN
   Client → POST /auth/login { email, password }
   Server:
     - Fetch user by email
     - Verify bcrypt hash
     - Generate JWT (expires in ACCESS_TOKEN_EXPIRE_MINUTES)
     - Return { access_token, token_type, user }

3. AUTHENTICATED REQUESTS
   Client → Any protected endpoint
   Header: Authorization: Bearer <JWT>
   Server:
     - deps.get_current_user extracts + verifies JWT
     - Loads user from DB (validates is_active)
     - Injects user object into route handler

4. ADMIN AUTHORIZATION
   Server:
     - deps.require_admin called after get_current_user
     - Checks user.role == "admin"
     - Returns 403 if role check fails

JWT Payload:
{
  "sub": "<user_id>",
  "exp": <unix_timestamp>
}
```

Token expiry is 7 days (10080 minutes) for improved UX in a support context. Tokens are not refreshed automatically; re-login is required after expiry.

---

## AI Processing Pipeline

See [ai-flow.md](ai-flow.md) for the complete AI documentation.

Summary:

1. **Intent Classification** — GPT-4o-mini classifies the message into one of: `billing`, `technical`, `account`, `shipping`, `general`, `escalation`.
2. **Escalation Decision** — Based on intent, explicit keywords, and conversation turn count.
3. **Response Generation** — Single API call combining intent detection and response generation via a structured system prompt.
4. **Confidence Scoring** — The model returns a 0.0–1.0 confidence float stored per-message.
5. **History Injection** — Up to the last 10 messages are included in the prompt for context continuity.

---

## Multi-Channel Architecture

SupportPilot is designed for multi-channel ingestion from the start. All channels converge into the same `conversations` and `messages` tables, distinguished by the `channel` field.

```
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│   Web Form      │   │   Gmail API     │   │ WhatsApp/Twilio │
│   (LIVE)        │   │   (READY)       │   │   (READY)       │
│                 │   │                 │   │                 │
│ POST /support/  │   │ Webhook/Polling │   │ Twilio Webhook  │
│    submit       │   │ Inbound Email   │   │ Inbound Message │
└────────┬────────┘   └────────┬────────┘   └────────┬────────┘
         │                     │                     │
         └─────────────────────┼─────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Channel Adapter   │
                    │   (normalize to     │
                    │   standard format)  │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   SupportService    │
                    │   (channel-agnostic │
                    │   processing)       │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │   conversations     │
                    │   channel = "web"   │
                    │   channel = "email" │
                    │   channel = "whats" │
                    └─────────────────────┘
```

To activate a new channel:
1. Implement a channel adapter that maps the inbound payload to `SupportSubmitRequest`.
2. Register a webhook endpoint or polling task.
3. Call `SupportService.process_submission()` — no changes to AI or business logic required.

---

## Scalability Considerations

### Current Architecture

- FastAPI is fully async; a single Railway instance can handle high concurrency.
- asyncpg connection pooling prevents DB connection exhaustion.
- Neon provides automatic scaling for the PostgreSQL layer.
- Vercel serves the frontend from a global CDN edge network.

### Near-Term Improvements

| Concern | Current | Recommended |
|---|---|---|
| AI Latency | Synchronous OpenAI call in request path | Move to background task (FastAPI BackgroundTasks or Celery) |
| Real-time Chat | Polling or page refresh | WebSocket endpoint (FastAPI native support) |
| Session Storage | Stateless JWT | Remains stateless; add Redis for token blacklisting on logout |
| Rate Limiting | None | Add slowapi middleware (Redis-backed) |
| File Uploads | Not implemented | S3/R2 presigned URLs for attachments |

### Long-Term Scaling Path

- Horizontal scaling behind a load balancer (Railway supports multiple replicas)
- Extract AI processing into a dedicated microservice or queue worker
- Read replicas on Neon for analytics/admin queries
- CDN caching for public-facing static support pages
- Multi-tenant database isolation via row-level security (PostgreSQL RLS)
