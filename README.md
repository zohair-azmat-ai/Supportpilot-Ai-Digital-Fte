# SupportPilot AI

<div align="center">

![SupportPilot AI](https://img.shields.io/badge/SupportPilot-AI-6366f1?style=for-the-badge&logo=openai&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js_14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![OpenAI](https://img.shields.io/badge/GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)

**A production-grade Digital FTE (AI Full-Time Employee) — an always-on, tool-based AI agent that handles customer support 24/7 with event-driven architecture, structured reasoning, and CRM-grade data persistence.**

[Live Demo](#live-demo) · [API Docs](#api-overview) · [Documentation](#documentation) · [Report Bug](../../issues)

</div>

---

## Live Demo

| | URL |
|---|---|
| **Frontend** | [supportpilot-ai-digital-fte.vercel.app](https://supportpilot-ai-digital-fte.vercel.app) |
| **Backend API** | [zohairazmat-supportpilot-ai-fte.hf.space](https://zohairazmat-supportpilot-ai-fte.hf.space) |
| **Interactive API Docs** | [zohairazmat-supportpilot-ai-fte.hf.space/docs](https://zohairazmat-supportpilot-ai-fte.hf.space/docs) |

**Deployed on:** Vercel (Next.js frontend) · Hugging Face Spaces (FastAPI backend) · Neon (PostgreSQL)

**Demo credentials:**
- Admin: `admin@supportpilot.ai` / `Admin123!`

> **Note:** The backend runs on Hugging Face Spaces free tier — it may take 30–60 seconds to wake up on first request.

---

## What Is SupportPilot AI?

SupportPilot AI is a full-stack AI-powered customer support platform built as a **Digital FTE** — an always-on AI agent that handles inbound support requests, classifies intent, generates contextual responses, creates and manages tickets, and escalates to human agents when needed.

The platform is built as a **single production-style monorepo** combining a Next.js frontend, FastAPI backend, PostgreSQL database, and OpenAI integration. It is designed to look and behave like a real SaaS product — not a hackathon demo.

**Built for:** portfolio, GitHub, LinkedIn, and YouTube showcase.
**Architecture goal:** clean enough to extend into a real product.

---

## Table of Contents

- [Live Demo](#live-demo)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Multi-Channel Design](#multi-channel-design)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Environment Variables](#environment-variables)
- [Deployment](#deployment)
- [Documentation](#documentation)
- [API Overview](#api-overview)
- [Scaling Roadmap](#scaling-roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

### Customer-Facing
- **AI-Powered Chat** — Real-time conversations with GPT-4o-mini. The AI detects intent, generates helpful replies, and knows when to escalate.
- **Web Support Form** — Submit a request with no account required; creates a conversation, an AI response, and a tracked ticket in one shot.
- **Ticket Dashboard** — Track every support request with status (open → in-progress → resolved), priority, and category filters.
- **Conversation History** — Full threaded message history with AI confidence scores and intent labels per message.
- **Secure Auth** — JWT-based signup and login with role-based access (customer / admin).

### Admin-Facing
- **Admin Overview** — Live stats: total users, open tickets, active conversations, resolution rate, escalations.
- **Ticket Management** — Full CRUD, inline status updates, priority management, assignee routing.
- **Conversation Explorer** — Browse all conversations across channels, inspect message threads, view escalation flags.
- **User Management** — View all registered users, roles, and account status.

### Platform
- **Tool-Based AI Agent** — Agent runs a strict 5-tool workflow: `get_customer_history` → `search_knowledge_base` → `create_ticket` → `[escalate_to_human]` → `send_response`. Every step is reasoned, logged, and auditable.
- **Event-Driven Architecture** — Dual-mode event bus: `InMemoryEventBus` for local dev (no setup), `KafkaEventBus` for production. Switch with one env var (`USE_KAFKA=true`).
- **Worker System** — `workers/message_processor.py` runs as a standalone Kafka consumer in production. Processes the full support pipeline outside the API process.
- **Intent Classification** — Every message is classified across 7 intent categories with a confidence score stored per message.
- **Smart Escalation** — Agent detects billing disputes, legal language, high frustration, and explicit human requests. Flags automatically via `escalate_to_human` tool.
- **CRM-Grade Schema** — Full schema: users, customers, customer_identifiers, conversations, messages, tickets, knowledge_base, agent_metrics.
- **Knowledge Base** — Keyword-searchable KB with pgvector-ready `embedding` field for Phase 2 RAG integration.
- **Agent Metrics** — Every AI interaction is recorded (intent, confidence, tools called, response time, escalation) for admin analytics.
- **Multi-Channel Architecture** — Web channel live; Gmail and WhatsApp adapters scaffolded and ready to activate with credentials.
- **Kubernetes-Ready** — Production manifests in `k8s/` for API deployment (2 replicas) and worker deployment.

---

## Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend Framework | Next.js 14 (App Router) | SSR, routing, React Server Components |
| UI Language | TypeScript 5 | End-to-end type safety |
| Styling | Tailwind CSS 3 | Utility-first dark premium UI |
| Forms | React Hook Form + Zod | Type-safe validation |
| HTTP Client | Axios | API calls with auth interceptors |
| Icons | Lucide React | Consistent icon system |
| Backend Framework | FastAPI | Async Python REST API |
| ORM | SQLAlchemy 2.0 (async) | Type-safe async database access |
| Migrations | Alembic | Schema versioning |
| DB Driver | asyncpg | Async PostgreSQL driver |
| Validation | Pydantic v2 | Request/response schemas |
| Auth | python-jose + bcrypt | JWT + bcrypt (direct, no passlib) |
| AI | OpenAI GPT-4o-mini | Intent detection, response generation, escalation |
| Database | PostgreSQL (Neon) | Serverless managed Postgres |
| Frontend Host | Vercel / Hugging Face Spaces | Edge-optimized Next.js deployment |
| Backend Host | Railway / Docker / Hugging Face Spaces | Containerized FastAPI deployment |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                             │
│   Browser — Next.js 14 App Router (Vercel)                      │
│   Auth ─── Dashboard ─── Chat ─── Tickets ─── Admin            │
└────────────────────────────┬────────────────────────────────────┘
                             │  HTTPS REST
┌────────────────────────────▼────────────────────────────────────┐
│                        API LAYER                                │
│   FastAPI  /api/v1/*  (Railway)                                 │
│   auth  ·  conversations  ·  messages  ·  tickets  ·  admin     │
│   support  ·  channels/email  ·  channels/whatsapp (webhooks)   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    CHANNEL ADAPTER LAYER                        │
│   Normalises inbound from any channel → InboundMessage          │
│   WebAdapter (live)  ·  EmailAdapter (scaffold)                 │
│   WhatsAppAdapter (scaffold)                                    │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      SERVICE LAYER                              │
│   AuthService  ·  ConversationService  ·  MessageService        │
│   TicketService  ·  SupportService  ·  AIService                │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    REPOSITORY LAYER                             │
│   UserRepo  ·  ConversationRepo  ·  MessageRepo  ·  TicketRepo  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
         ┌──────────────────┴──────────────────┐
         │                                     │
┌────────▼────────┐                  ┌─────────▼────────┐
│   PostgreSQL    │                  │   OpenAI API     │
│  (Neon — prod)  │                  │  GPT-4o-mini     │
│  (local — dev)  │                  │  JSON mode       │
└─────────────────┘                  └──────────────────┘
```

The backend enforces a strict **Route → Channel Adapter → Event Bus → Service → Agent → Repository → Database** separation. Routes handle HTTP. Adapters normalise channel-specific payloads. The event bus decouples ingest from processing. Services orchestrate the pipeline. The AI agent runs structured tool calls. Repositories abstract all queries.

---

## Multi-Channel Design

SupportPilot AI is built channel-first. Every inbound message — regardless of source — flows through a channel adapter that normalises it into a shared `InboundMessage` schema before hitting the support pipeline.

| Channel | Status | Entry point |
|---|---|---|
| **Web Form** | ✅ Live | `POST /api/v1/support/submit` |
| **Web Chat** | ✅ Live | `POST /api/v1/conversations/{id}/messages` |
| **Gmail / Email** | 🔧 Scaffolded | `backend/app/channels/email.py` — add credentials to activate |
| **WhatsApp** | 🔧 Scaffolded | `backend/app/channels/whatsapp.py` — add Twilio credentials to activate |

### How the adapter pattern works

```python
# Every channel implements the same two-method interface:

class BaseChannelAdapter(ABC):
    async def parse_inbound(self, payload: dict) -> InboundMessage: ...
    async def send_response(self, recipient: str, message: str) -> bool: ...

# SupportService receives an InboundMessage — it never sees raw channel payloads.
# Adding a new channel (Slack, SMS, in-app) = add one new adapter file.
```

Activating Gmail or WhatsApp requires only adding credentials to `.env` and removing the `NotImplementedError` guard in the respective adapter. The service layer requires **no changes**.

For the Kafka-based async queue architecture (Phase 3), see [docs/specs/scaling-architecture.md](docs/specs/scaling-architecture.md).

---

## Project Structure

```
supportpilot-ai/                        ← Single monorepo
├── README.md
├── .gitignore
│
├── frontend/                           # Next.js 14 application
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.mjs
│   ├── .env.local                      # (not committed)
│   │
│   ├── app/                            # App Router pages
│   │   ├── layout.tsx                  # Root layout + AuthProvider
│   │   ├── page.tsx                    # Landing page
│   │   ├── globals.css
│   │   ├── (auth)/                     # Auth route group
│   │   │   ├── login/page.tsx
│   │   │   └── signup/page.tsx
│   │   ├── (customer)/                 # Customer portal
│   │   │   ├── dashboard/page.tsx
│   │   │   ├── chat/page.tsx           # Conversations list
│   │   │   ├── chat/[id]/page.tsx      # Chat thread
│   │   │   ├── tickets/page.tsx
│   │   │   ├── support/page.tsx        # Web support form
│   │   │   └── settings/page.tsx
│   │   └── (admin)/admin/              # Admin portal
│   │       ├── page.tsx                # Overview dashboard
│   │       ├── tickets/page.tsx
│   │       ├── conversations/page.tsx
│   │       ├── users/page.tsx
│   │       └── analytics/page.tsx
│   │
│   ├── components/
│   │   ├── ui/                         # Button, Input, Card, Badge, Modal…
│   │   ├── layout/                     # Sidebar, Header, DashboardLayout
│   │   ├── chat/                       # ChatWindow, MessageBubble, ChatInput
│   │   ├── tickets/                    # TicketCard, TicketTable
│   │   ├── dashboard/                  # StatsCard, RecentTickets
│   │   └── forms/                      # SupportForm
│   │
│   ├── context/AuthContext.tsx
│   ├── hooks/                          # useAuth, useConversations, useTickets
│   ├── lib/                            # api.ts, auth.ts, utils.ts
│   └── types/index.ts                  # Shared TypeScript types
│
├── backend/                            # FastAPI application
│   ├── main.py                         # App entry point
│   ├── requirements.txt
│   ├── .env.example
│   │
│   ├── app/
│   │   ├── core/
│   │   │   ├── config.py               # Pydantic settings
│   │   │   ├── database.py             # Async SQLAlchemy engine
│   │   │   ├── security.py             # JWT + bcrypt utilities
│   │   │   └── deps.py                 # FastAPI dependencies
│   │   ├── models/                     # SQLAlchemy ORM models
│   │   │   ├── user.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   └── ticket.py
│   │   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── repositories/               # Data access layer (per entity)
│   │   ├── services/                   # Business logic layer
│   │   │   ├── auth.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py              # Orchestrates AI call
│   │   │   ├── ticket.py
│   │   │   └── support.py              # Web form pipeline
│   │   ├── channels/                   # ← Channel adapter layer
│   │   │   ├── base.py                 # BaseChannelAdapter + InboundMessage
│   │   │   ├── web.py                  # Live — web form + chat
│   │   │   ├── email.py                # Scaffolded — Gmail API
│   │   │   └── whatsapp.py             # Scaffolded — Twilio WhatsApp
│   │   ├── events/                     # ← Event bus layer
│   │   │   ├── topics.py               # Kafka topic constants
│   │   │   ├── schemas.py              # Pydantic event payload schemas
│   │   │   ├── bus.py                  # EventBus ABC + InMemoryEventBus + factory
│   │   │   └── kafka_bus.py            # KafkaEventBus (production)
│   │   ├── ai/
│   │   │   ├── client.py               # AsyncOpenAI singleton
│   │   │   ├── prompts.py              # System prompts
│   │   │   ├── service.py              # AIResponse dataclass
│   │   │   ├── tools.py                # 5 tool definitions + ToolExecutor
│   │   │   └── agent.py                # SupportAgent — tool-calling loop
│   │   ├── models/
│   │   │   ├── user.py / conversation.py / message.py / ticket.py
│   │   │   ├── customer.py             # Customer + CustomerIdentifier (CRM)
│   │   │   ├── knowledge_base.py       # KB articles (pgvector-ready)
│   │   │   └── agent_metrics.py        # Per-interaction AI metrics
│   │   ├── api/v1/routes/              # HTTP route handlers
│   │   └── utils/logging.py
│   │
│   ├── workers/                        # ← Kafka worker processes
│   │   ├── base.py                     # BaseWorker — consume loop + SIGTERM
│   │   ├── message_processor.py        # Full support pipeline
│   │   └── main.py                     # Entry point: python -m workers.main
│   │
│   └── alembic/                        # Database migrations
│
├── docs/
│   ├── architecture.md
│   ├── api-spec.md
│   ├── db-schema.md
│   ├── ai-flow.md
│   ├── deployment.md
│   └── specs/
│       ├── customer-support-spec.md    # AI rules, escalation, channel behavior
│       ├── discovery-log.md            # Engineering decisions + trade-off log
│       ├── prompt-history.md           # AI prompt versions + testing notes
│       └── scaling-architecture.md    # Kafka / K8s future architecture plan
│
└── scripts/
    ├── seed.py                         # Create sample users, tickets, chats
    └── init_db.sh                      # One-command setup + migrations
```

---

## Getting Started

### Prerequisites

- **Node.js** >= 18.x and npm >= 9.x
- **Python** >= 3.11
- **PostgreSQL** >= 15 (or a [Neon](https://neon.tech) account)
- **OpenAI API Key** — [platform.openai.com](https://platform.openai.com)
- **Git**

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/supportpilot-ai.git
cd supportpilot-ai
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate       # Linux/macOS
# venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, SECRET_KEY, OPENAI_API_KEY

# Run database migrations
alembic upgrade head

# (Optional) Seed sample data
python ../scripts/seed.py

# Start the development server
uvicorn main:app --reload --port 8000
```

API available at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

### 3. Frontend Setup

```bash
cd frontend

npm install

# .env.local is pre-configured for local development
# NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1

npm run dev
```

App available at `http://localhost:3000`.

### 4. Database Setup

**Option A — Local PostgreSQL:**
```bash
psql -U postgres -c "CREATE DATABASE supportpilot;"
# Set DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/supportpilot
```

**Option B — Neon (recommended):**
1. Create a free project at [neon.tech](https://neon.tech)
2. Copy the `postgresql+asyncpg://...` connection string
3. Set it as `DATABASE_URL` in `backend/.env`

### 5. Quick Start (one command)

```bash
chmod +x scripts/init_db.sh
./scripts/init_db.sh --seed
```

Handles venv, install, migrations, and seeding in one step.

**Seed credentials:**
- Admin: `admin@supportpilot.ai` / `Admin123!`

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Description | Example |
|---|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@host/db` |
| `SECRET_KEY` | Yes | JWT signing key (generate with `openssl rand -hex 32`) | `a1b2c3...` |
| `ALGORITHM` | Yes | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | Token lifetime | `10080` (7 days) |
| `OPENAI_API_KEY` | Yes | OpenAI API key | `sk-...` |
| `OPENAI_MODEL` | Yes | Model identifier | `gpt-4o-mini` |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins | `http://localhost:3000` |
| `ENVIRONMENT` | Yes | Runtime environment | `development` or `production` |
| `USE_KAFKA` | No | `false` = InMemoryBus (dev), `true` = Kafka (prod) | `false` |
| `KAFKA_BOOTSTRAP_SERVERS` | If Kafka | Kafka broker address | `localhost:9092` |

### Frontend (`frontend/.env.local`)

| Variable | Required | Description | Example |
|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Backend API base URL | `http://localhost:8000/api/v1` |

---

## Deployment

### Frontend — Vercel

1. Push to GitHub.
2. Import the project at [vercel.com/new](https://vercel.com/new).
3. Set **Root Directory** to `frontend`.
4. Add `NEXT_PUBLIC_API_URL` → your backend URL.
5. Deploy. Vercel auto-detects Next.js.

### Backend — Docker (Railway / Fly.io / any container host)

A `Dockerfile` is included in `backend/`. Build and run locally:

```bash
cd backend
docker build -t supportpilot-backend .
docker run -p 8000:8000 --env-file .env supportpilot-backend
```

On **Railway**: connect your GitHub repo, set root directory to `backend`, and Railway will auto-detect and build the Dockerfile.

### Backend — Hugging Face Spaces

SupportPilot's FastAPI backend can be deployed as a [Hugging Face Space](https://huggingface.co/spaces) using the **Docker SDK**:

1. Create a new Space → SDK: **Docker**.
2. Push the `backend/` directory (with `Dockerfile`) to the Space repo.
3. Add all environment variables in Space Settings → Repository Secrets.
4. The Space exposes port `7860` — the Dockerfile maps uvicorn to `$PORT` (defaults to 7860 on HF).

> See [docs/deployment.md](docs/deployment.md) for the full Hugging Face deployment walkthrough.

### Database — Neon

1. Sign up at [neon.tech](https://neon.tech).
2. Create a new project and database.
3. Copy the connection string — you can use the raw `postgresql://...?sslmode=require` string; the backend normalises it automatically.
4. Set it as `DATABASE_URL` and run: `alembic upgrade head`

For detailed step-by-step instructions, see [docs/deployment.md](docs/deployment.md).

---

## Documentation

| Document | Description |
|---|---|
| [docs/architecture.md](docs/architecture.md) | System design, data flow, and layer breakdown |
| [docs/api-spec.md](docs/api-spec.md) | Full API reference with request/response examples |
| [docs/db-schema.md](docs/db-schema.md) | Database schema, entities, and relationships |
| [docs/ai-flow.md](docs/ai-flow.md) | AI service design, prompt strategy, and escalation logic |
| [docs/deployment.md](docs/deployment.md) | Step-by-step deployment guide (Vercel + Railway + Neon) |
| [docs/specs/customer-support-spec.md](docs/specs/customer-support-spec.md) | AI behavior rules, escalation triggers, channel definitions |
| [docs/specs/discovery-log.md](docs/specs/discovery-log.md) | Engineering decisions and technical trade-off log |
| [docs/specs/prompt-history.md](docs/specs/prompt-history.md) | AI prompt versions, rationale, and regression test scenarios |
| [docs/specs/scaling-architecture.md](docs/specs/scaling-architecture.md) | Kafka + Kubernetes future-ready architecture plan |
| [docs/dev-notes.md](docs/dev-notes.md) | Known issues, local-dev quirks, and engineering workarounds |

---

## API Overview

All endpoints are prefixed with `/api/v1`.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/auth/signup` | Public | Register a new user |
| POST | `/auth/login` | Public | Login and receive JWT |
| GET | `/auth/me` | Required | Get current user profile |
| GET | `/conversations` | Required | List user's conversations |
| POST | `/conversations` | Required | Start a new conversation |
| GET | `/conversations/{id}` | Required | Conversation thread with messages |
| POST | `/conversations/{id}/messages` | Required | Send message → triggers AI reply |
| GET | `/tickets` | Required | List user's tickets |
| POST | `/tickets` | Required | Create a ticket |
| GET | `/tickets/{id}` | Required | Get single ticket |
| PATCH | `/tickets/{id}` | Required | Update status / priority |
| POST | `/support/submit` | Public | Web support form submission |
| GET | `/admin/stats` | Admin | Platform statistics |
| GET | `/admin/tickets` | Admin | All tickets (paginated, filterable) |
| GET | `/admin/conversations` | Admin | All conversations |
| GET | `/admin/users` | Admin | All registered users |
| PATCH | `/admin/tickets/{id}` | Admin | Update any ticket |

For full schemas, see [docs/api-spec.md](docs/api-spec.md).

---

## Scaling Roadmap

| Phase | What | Status |
|---|---|---|
| **Phase 1 — Digital FTE MVP** | Tool-based AI agent (5 tools), event bus (dual-mode), worker system, CRM schema, K8s manifests | ✅ Implemented |
| **Phase 2 — Channels + Streaming** | Activate Gmail/WhatsApp adapters, OpenAI streaming, WebSocket real-time push | Next — add credentials |
| **Phase 3 — Full Kafka** | Set `USE_KAFKA=true`, run `python -m workers.main` as separate process, scale workers | When traffic demands it |
| **Phase 4 — Kubernetes** | Apply `k8s/` manifests, HPA on Kafka consumer lag (KEDA), multi-tenant workspaces | Enterprise / B2B |

The event bus abstraction (`backend/app/events/bus.py`) and worker system (`backend/workers/`) are implemented. Switching from inline to Kafka processing requires only `USE_KAFKA=true` in `.env`. See [docs/specs/scaling-architecture.md](docs/specs/scaling-architecture.md) for the full architecture path.

---

## Future Features

- [ ] **Gmail channel** — Inbound email parsing, auto-reply in thread, ticket creation
- [ ] **WhatsApp channel** — Twilio WhatsApp Business API for conversational support
- [ ] **RAG knowledge base** — Company docs embedded + retrieved with pgvector / Pinecone
- [ ] **WebSocket streaming** — Real-time AI response streaming to the chat UI
- [ ] **Human handoff UI** — Admin live-chat takeover for escalated conversations
- [ ] **SLA automation** — Auto-escalation on time/priority thresholds
- [ ] **Fine-tuned model** — Domain-specific fine-tuning on resolved ticket history
- [ ] **Multi-tenant workspaces** — Workspace isolation for B2B SaaS model
- [ ] **Webhook integrations** — Slack/Teams alerts on ticket events
- [ ] **Analytics charts** — Resolution time, CSAT scores, volume trends over time

---

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make focused, well-named commits
4. Ensure the backend starts: `uvicorn main:app --reload`
5. Ensure the frontend builds: `npm run build`
6. Open a Pull Request against `main`

Code conventions:
- **Backend:** PEP 8, async/await throughout, typed function signatures
- **Frontend:** TypeScript strict mode, functional components, Tailwind only

---

## License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 Zohair

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```
