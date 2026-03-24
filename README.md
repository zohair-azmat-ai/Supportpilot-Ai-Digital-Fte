<div align="center">

# 🚀 SupportPilot AI — Digital Customer Support FTE

**Production-grade AI support platform with chat, tickets, escalation, and analytics.**

> ⚡ Live on Vercel &nbsp;·&nbsp; 📊 Full REST API &nbsp;·&nbsp; 🧠 AI-Powered Responses &nbsp;·&nbsp; 🔁 Real-time Processing

<br/>

[![Next.js](https://img.shields.io/badge/Next.js_14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![OpenAI](https://img.shields.io/badge/OpenAI_GPT--4o-412991?style=for-the-badge&logo=openai&logoColor=white)](https://platform.openai.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Status: Live](https://img.shields.io/badge/Status-Live-22c55e?style=for-the-badge&logo=vercel&logoColor=white)](https://supportpilot-ai-digital-fte.vercel.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-f59e0b?style=for-the-badge)](LICENSE)

<br/>

[🚀 Live Demo](#-live-demo) &nbsp;·&nbsp; [📐 Architecture](#-architecture) &nbsp;·&nbsp; [⚡ Quick Start](#-getting-started) &nbsp;·&nbsp; [📖 API Docs](https://zohairazmat-supportpilot-ai-fte.hf.space/docs) &nbsp;·&nbsp; [🐛 Report Bug](../../issues)

</div>

---

## 🚀 Live Demo

<div align="center">

| Service | Link | Status |
|:-------:|:-----|:------:|
| 🌐 **Frontend** | [supportpilot-ai-digital-fte.vercel.app](https://supportpilot-ai-digital-fte.vercel.app) | ✅ Live |
| ⚡ **Backend API** | [zohairazmat-supportpilot-ai-fte.hf.space](https://zohairazmat-supportpilot-ai-fte.hf.space) | ✅ Live |
| 📖 **API Docs** | [.../docs](https://zohairazmat-supportpilot-ai-fte.hf.space/docs) | ✅ Live |

</div>

<br/>

**Deployed on:** &nbsp; Vercel (Next.js) &nbsp;·&nbsp; Hugging Face Spaces (FastAPI · Docker) &nbsp;·&nbsp; Neon (PostgreSQL)

**Demo credentials:**

```
Admin portal  →  admin@supportpilot.ai  /  Admin123!
```

> ⚠️ **First request may take 30–60 seconds due to cold start (HF Spaces free tier)**

---

## ✨ Why This Project Stands Out

This is not a tutorial project or a hackathon demo. It is a **production-style monorepo** built to the standard of a well-engineered SaaS company.

| &nbsp; | What | Why it matters |
|:------:|:-----|:---------------|
| 🏗️ | **Full-stack, live deployment** | **Production-ready infrastructure** — Frontend on Vercel, backend on HF Spaces, DB on Neon, all wired together and publicly accessible |
| 🤖 | **Tool-based AI agent** | **Auditable reasoning loop** — runs a strict 5-tool sequence; every decision is logged and explainable |
| 📊 | **Dual portal system** | **Role-based access control** — separate customer and admin dashboards secured with JWT |
| 🔌 | **Event-driven architecture** | **Zero-code bus swap** — InMemoryBus for dev, KafkaEventBus for prod, one env var to switch |
| 📡 | **Multi-channel design** | **Unified customer history** — adapter pattern normalises Web, Gmail, and WhatsApp; same identity cross-channel; email thread continuity via `thread_id` |
| 📈 | **CRM-grade schema** | **9 relational tables** — users, customers, conversations, messages, tickets, KB, agent_metrics, system_events |
| ☸️ | **Scale-ready from day one** | **Kubernetes-ready** — Kafka workers and K8s manifests already committed for the next phase |

---

## 📋 Table of Contents

- [🚀 Live Demo](#-live-demo)
- [✨ Why This Project Stands Out](#-why-this-project-stands-out)
- [🎯 Features](#-features)
- [🛠 Tech Stack](#-tech-stack)
- [📐 Architecture](#-architecture)
- [📡 Multi-Channel Design](#-multi-channel-design)
- [📁 Project Structure](#-project-structure)
- [⚡ Getting Started](#-getting-started)
- [🔐 Environment Variables](#-environment-variables)
- [☁️ Deployment](#️-deployment)
- [🔌 API Overview](#-api-overview)
- [📖 Documentation](#-documentation)
- [📈 Scaling Roadmap](#-scaling-roadmap)
- [🔮 Future Features](#-future-features)
- [⭐ Support & Connect](#-support--connect)
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## 🎯 Features

### Customer Portal

| Feature | Description |
|:--------|:------------|
| **AI-Powered Chat** | Real-time GPT-4o-mini conversations with intent detection, context memory, and smart escalation |
| **Web Support Form** | No account required — submit a request and receive an AI response with a tracked ticket instantly |
| **Ticket Dashboard** | Track every request with status filters (open → in-progress → resolved), priority, and categories |
| **Conversation History** | Threaded message history with per-message AI confidence scores and intent labels |
| **Secure Auth** | JWT-based signup and login with role-based access control (customer / admin) |

### Admin Portal

| Feature | Description |
|:--------|:------------|
| **Analytics Dashboard** | Live stats — users, open tickets, active conversations, resolution rate, escalation counts |
| **Ticket Management** | Full CRUD with inline status updates, priority management, and category routing |
| **Conversation Explorer** | Browse all conversations, inspect threads, view AI confidence and escalation flags |
| **User Management** | View all registered users, roles, account status, and activity |

### Platform & AI

| Feature | Description |
|:--------|:------------|
| **5-Tool AI Agent** | Strict tool order: `get_history` → `search_KB` → `create_ticket` → `[escalate]` → `send_response` |
| **Smart Escalation** | Detects billing disputes, legal language, repeated issues, and frustration signals automatically |
| **Intent Classification** | 7 categories (technical, billing, account, complaint, feature_request, general, urgent) + confidence |
| **Conversation Memory** | Pre-flight check detects repeated topics across history before calling OpenAI |
| **Event-Driven Bus** | InMemoryEventBus for dev · KafkaEventBus for prod — zero code change to switch |
| **Knowledge Base** | Keyword-searchable articles with pgvector-ready `embedding` field for Phase 2 RAG |
| **Agent Metrics** | Every AI call logged: intent, confidence, tools, response time, escalation status |
| **Multi-Channel** | Web live · Gmail scaffolded · WhatsApp scaffolded — activate with credentials only |

---

## 🛠 Tech Stack

### Frontend

| Technology | Version | Purpose |
|:-----------|:-------:|:--------|
| Next.js | 14 | SSR, App Router, React Server Components |
| TypeScript | 5 | End-to-end type safety |
| Tailwind CSS | 3 | Utility-first dark premium UI |
| React Hook Form + Zod | — | Type-safe form validation |
| Axios | — | API client with JWT auth interceptors |
| Lucide React | — | Consistent icon system |

### Backend

| Technology | Version | Purpose |
|:-----------|:-------:|:--------|
| FastAPI | Latest | Async Python REST API |
| SQLAlchemy | 2.0 | Type-safe async ORM |
| Alembic | — | Schema migrations |
| asyncpg | — | Async PostgreSQL driver |
| Pydantic | v2 | Request/response schemas and settings |
| python-jose + bcrypt | — | JWT signing + password hashing |

### AI, Data & Deployment

| Technology | Purpose |
|:-----------|:--------|
| OpenAI GPT-4o-mini | Intent detection, response generation, tool-calling agent loop |
| PostgreSQL — Neon | Serverless managed Postgres with pgvector support |
| Apache Kafka | Async event processing in production (`USE_KAFKA=true`) |
| Vercel | Next.js 14 frontend — edge-optimised global deployment |
| Hugging Face Spaces | FastAPI backend — Docker container deployment |

---

## 📐 Architecture

<br/>

```mermaid
flowchart TD
    Browser(["🌐 Browser\nNext.js 14 · Vercel"])

    subgraph BackendLayer["  ⚡ FastAPI Backend — Hugging Face Spaces  "]
        direction TB
        Routes["🔀 Route Handlers\n/auth · /chat · /tickets · /admin · /support"]
        Adapters["📡 Channel Adapters\nWeb ✅   Email 🔧   WhatsApp 🔧"]
        EventBus["🔄 Event Bus\nInMemoryBus dev  ·  KafkaBus prod"]
        Services["⚙️ Services\nAuth · Chat · Tickets · Support · AI"]
    end

    subgraph AgentLayer["  🤖 AI Agent — GPT-4o-mini  "]
        direction TB
        Agent["🧠 SupportAgent\nTool-calling loop · max 8 iterations"]
        Tools["🛠️ 5-Tool Workflow\nhistory → KB → ticket → escalate → respond"]
        GPT["✨ OpenAI API\nGPT-4o-mini · JSON mode · temp 0.3"]
    end

    subgraph DataLayer["  🗄️ Data Layer — Neon PostgreSQL  "]
        direction TB
        Repos["📦 Repositories\nUser · Conv · Message · Ticket · Metrics · KB"]
        PG[("🐘 PostgreSQL\nNeon Serverless")]
        KBase[("📚 Knowledge Base\npgvector-ready")]
    end

    Browser -->|"HTTPS REST"| Routes
    Routes --> Adapters
    Adapters --> EventBus
    EventBus --> Services
    Services --> Agent
    Agent --> Tools
    Tools --> GPT
    Tools --> Repos
    Services --> Repos
    Repos --> PG
    Repos --> KBase

    classDef frontendStyle fill:#4f46e5,stroke:#3730a3,stroke-width:2px,color:#fff
    classDef backendStyle fill:#0369a1,stroke:#075985,stroke-width:2px,color:#fff
    classDef aiStyle fill:#6d28d9,stroke:#5b21b6,stroke-width:2px,color:#fff
    classDef gptStyle fill:#312e81,stroke:#1e1b4b,stroke-width:2px,color:#fff
    classDef dbStyle fill:#065f46,stroke:#064e3b,stroke-width:2px,color:#fff

    class Browser frontendStyle
    class Routes,Adapters,EventBus,Services backendStyle
    class Agent,Tools aiStyle
    class GPT gptStyle
    class Repos,PG,KBase dbStyle
```

<br/>

**Layer responsibilities:**

| Layer | Responsibility |
|:------|:---------------|
| **Routes** | HTTP handling — auth, validation, response serialisation |
| **Channel Adapters** | Normalise channel-specific payloads into a shared `InboundMessage` schema |
| **Event Bus** | Decouple ingest from processing — swap InMemory → Kafka with one env var |
| **Services** | Orchestrate the pipeline — auth, ticket creation, message flow |
| **AI Agent** | Run structured tool calls, classify intent, generate responses, decide escalation |
| **Repositories** | Abstract all database queries — one class per entity |

---

## 📡 Multi-Channel Design

Every inbound message — regardless of origin — is normalised into a shared `InboundMessage` schema before reaching the support pipeline. The service layer never sees raw channel payloads.

| Channel | Status | Entry Point |
|:--------|:------:|:------------|
| **Web Chat** | ✅ Live | `POST /api/v1/conversations/{id}/messages` |
| **Web Support Form** | ✅ Live | `POST /api/v1/support/submit` |
| **Gmail / Email** | 🟡 Activation-ready | `POST /api/v1/channels/email/inbound` — set `GMAIL_ENABLED=true` + credentials |
| **WhatsApp** | 🟡 Activation-ready | `POST /api/v1/channels/whatsapp/inbound` — set `TWILIO_ENABLED=true` + credentials |

**Unified customer identity across channels:**

- Same email on web and Gmail → one `Customer` record, shared support history
- Same phone on WhatsApp → linked via `CustomerIdentifier(channel='whatsapp')`
- AI context builder surfaces cross-channel history to the agent on every request
- Multi-channel activity detected automatically — agent informed when customer contacts from multiple channels

**Email thread continuity:**

- Gmail `thread_id` stored on the `Conversation` record
- Replies in the same Gmail thread resume the same conversation in SupportPilot
- WhatsApp sessions keyed on sender phone — one active conversation per sender

**Safe when credentials are absent:**

- `GMAIL_ENABLED=false` (default) — webhook returns `503`, polling skips silently; app starts normally
- `TWILIO_ENABLED=false` (default) — webhook returns `503`; no crash, no startup warning
- Both channels log a clear message when send_response is called without credentials

**Adding a new channel requires only one file:**

```python
class BaseChannelAdapter(ABC):
    async def parse_inbound(self, payload: dict) -> InboundMessage: ...
    async def send_response(self, recipient: str, message: str) -> bool: ...

# SupportService only ever receives InboundMessage — channel-agnostic by design.
# thread_id and external_id on InboundMessage carry channel-specific metadata cleanly.
```

---

## 📁 Project Structure

```
supportpilot-ai/                        ← Single production monorepo
├── README.md
├── .gitignore
│
├── frontend/                           # Next.js 14 application
│   ├── app/
│   │   ├── (auth)/                     # Login · Signup
│   │   ├── (customer)/                 # Dashboard · Chat · Tickets · Support · Settings
│   │   └── (admin)/admin/              # Overview · Tickets · Conversations · Users · Analytics
│   ├── components/
│   │   ├── ui/                         # Button, Input, Card, Badge, Modal, Spinner...
│   │   ├── layout/                     # Sidebar, Header, DashboardLayout
│   │   ├── chat/                       # ChatWindow, MessageBubble, ChatInput
│   │   ├── tickets/                    # TicketCard, TicketTable
│   │   └── forms/                      # SupportForm
│   ├── context/                        # AuthContext, ToastContext
│   ├── hooks/                          # useAuth, useConversations, useTickets
│   ├── lib/                            # api.ts, auth.ts, utils.ts
│   └── types/index.ts                  # Shared TypeScript interfaces
│
├── backend/                            # FastAPI application
│   ├── main.py                         # App entry point + lifespan
│   ├── Dockerfile                      # HF Spaces / Railway container
│   └── app/
│       ├── core/                       # config · database · security · deps
│       ├── models/                     # SQLAlchemy ORM models (8 tables)
│       ├── schemas/                    # Pydantic v2 schemas
│       ├── repositories/               # Data access — one class per entity
│       ├── services/                   # Business logic — auth · chat · tickets
│       ├── channels/                   # Adapters — base · web · email · whatsapp
│       ├── events/                     # Event bus — InMemory · Kafka · topics
│       ├── ai/
│       │   ├── agent.py                # SupportAgent — 5-tool loop
│       │   ├── tools.py                # Tool definitions + ToolExecutor
│       │   ├── service.py              # AIResponse dataclass + fallback logic
│       │   └── client.py               # AsyncOpenAI singleton
│       └── api/v1/routes/              # HTTP route handlers
│
├── workers/                            # Kafka consumer workers
├── docs/                               # Architecture, API spec, DB schema, AI flow
├── scripts/                            # seed.py, init_db.sh
└── k8s/                                # Kubernetes manifests
```

---

## ⚡ Getting Started

### Prerequisites

- **Node.js** ≥ 18 and **npm** ≥ 9
- **Python** ≥ 3.11
- **PostgreSQL** ≥ 15 — or a free [Neon](https://neon.tech) account
- **OpenAI API Key** — [platform.openai.com](https://platform.openai.com)

### 1. Clone

```bash
git clone https://github.com/zohair-azmat-ai/Supportpilot-Ai-Digital-Fte.git
cd Supportpilot-Ai-Digital-Fte
```

### 2. Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate        # macOS / Linux
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL, SECRET_KEY, OPENAI_API_KEY

# Run migrations
alembic upgrade head

# Optional: seed sample data
python ../scripts/seed.py

# Start dev server
uvicorn main:app --reload --port 8000
```

> API: `http://localhost:8000` &nbsp;·&nbsp; Swagger UI: `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend

npm install
cp .env.local.example .env.local   # pre-configured for localhost

npm run dev
```

> App: `http://localhost:3000`

### 4. Database

**Option A — Neon (recommended, free tier):**

1. Sign up at [neon.tech](https://neon.tech) and create a project
2. Copy the connection string
3. Set `DATABASE_URL=postgresql+asyncpg://...?sslmode=require` in `backend/.env`

**Option B — Local PostgreSQL:**

```bash
psql -U postgres -c "CREATE DATABASE supportpilot;"
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/supportpilot
```

### 5. One-Command Setup

```bash
chmod +x scripts/init_db.sh
./scripts/init_db.sh --seed
```

Handles venv, install, migrations, and seeding in one step.

**Seed admin credentials:** `admin@supportpilot.ai` / `Admin123!`

---

## 🔐 Environment Variables

### Backend — `backend/.env`

| Variable | Required | Description | Example |
|:---------|:--------:|:------------|:--------|
| `DATABASE_URL` | ✅ | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@host/db` |
| `SECRET_KEY` | ✅ | JWT signing key — `openssl rand -hex 32` | `a1b2c3...` |
| `ALGORITHM` | ✅ | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ✅ | Token lifetime in minutes | `10080` |
| `OPENAI_API_KEY` | ✅ | OpenAI API key | `sk-...` |
| `OPENAI_MODEL` | ✅ | Model identifier | `gpt-4o-mini` |
| `CORS_ORIGINS` | ✅ | JSON array of allowed origins | `["http://localhost:3000"]` |
| `ENVIRONMENT` | ✅ | Runtime flag | `development` or `production` |
| `USE_KAFKA` | — | Event bus mode | `false` dev · `true` prod |
| `KAFKA_BOOTSTRAP_SERVERS` | If Kafka | Kafka broker address | `localhost:9092` |

### Frontend — `frontend/.env.local`

| Variable | Required | Description |
|:---------|:--------:|:------------|
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API base URL — `http://localhost:8000/api/v1` |

---

## ☁️ Deployment

### Frontend — Vercel

1. Push to GitHub
2. Import at [vercel.com/new](https://vercel.com/new) — set **Root Directory** to `frontend`
3. Add `NEXT_PUBLIC_API_URL` → your backend URL
4. Deploy — Vercel auto-detects Next.js

### Backend — Hugging Face Spaces

1. Create a new Space → SDK: **Docker**
2. Add all env vars under Space Settings → **Repository Secrets**
3. Push the backend:

```bash
git remote add hf https://huggingface.co/spaces/<your-username>/<space-name>
git push hf main
```

### Backend — Docker (Railway / Fly.io)

```bash
cd backend
docker build -t supportpilot-backend .
docker run -p 8000:8000 --env-file .env supportpilot-backend
```

### Database — Neon

1. Sign up at [neon.tech](https://neon.tech) and create a project
2. Copy the pooled connection string
3. Set `DATABASE_URL` and run `alembic upgrade head`

> See [docs/deployment.md](docs/deployment.md) for the complete walkthrough.

---

## 🔌 API Overview

All endpoints are prefixed with `/api/v1`. &nbsp; Interactive docs → [`/docs`](https://zohairazmat-supportpilot-ai-fte.hf.space/docs)

| Method | Endpoint | Auth | Description |
|:------:|:---------|:----:|:------------|
| `POST` | `/auth/signup` | Public | Register a new user |
| `POST` | `/auth/login` | Public | Login and receive JWT |
| `GET` | `/auth/me` | 🔒 | Get current user profile |
| `GET` | `/conversations` | 🔒 | List user's conversations |
| `POST` | `/conversations` | 🔒 | Start a new conversation |
| `GET` | `/conversations/{id}` | 🔒 | Conversation thread with messages |
| `POST` | `/conversations/{id}/messages` | 🔒 | Send message → triggers AI agent |
| `GET` | `/tickets` | 🔒 | List user's tickets |
| `POST` | `/tickets` | 🔒 | Create a ticket |
| `PATCH` | `/tickets/{id}` | 🔒 | Update ticket status / priority |
| `POST` | `/support/submit` | Public | Web form → AI response + ticket |
| `GET` | `/admin/stats` | 👑 | Platform statistics |
| `GET` | `/admin/tickets` | 👑 | All tickets — paginated, filterable |
| `PATCH` | `/admin/tickets/{id}` | 👑 | Update any ticket |
| `GET` | `/admin/conversations` | 👑 | All conversations |
| `GET` | `/admin/users` | 👑 | All registered users |
| `GET` | `/metrics/overview` | 👑 | AI agent performance stats |
| `GET` | `/metrics/channels` | 👑 | Per-channel breakdown |
| `GET` | `/metrics/escalations` | 👑 | Escalation records and rates |
| `GET` | `/metrics/events` | 👑 | Event log analytics (by type, channel, intent) |
| `POST` | `/channels/email/inbound` | Public | Gmail Pub/Sub webhook (GMAIL_ENABLED) |
| `POST` | `/channels/whatsapp/inbound` | Public | Twilio WhatsApp webhook (TWILIO_ENABLED) |

> Full request/response schemas → [docs/api-spec.md](docs/api-spec.md)

---

## 📖 Documentation

| Document | What's Inside |
|:---------|:--------------|
| [docs/architecture.md](docs/architecture.md) | System design, data flow, and layer responsibilities |
| [docs/api-spec.md](docs/api-spec.md) | Full API reference with request/response examples |
| [docs/db-schema.md](docs/db-schema.md) | Database schema, entity relationships, and indexes |
| [docs/ai-flow.md](docs/ai-flow.md) | AI agent design, prompt strategy, tool execution, escalation logic |
| [docs/deployment.md](docs/deployment.md) | Step-by-step deployment guide — Vercel + HF Spaces + Neon |
| [docs/specs/customer-support-spec.md](docs/specs/customer-support-spec.md) | AI behaviour rules, escalation triggers, channel definitions |
| [docs/specs/discovery-log.md](docs/specs/discovery-log.md) | Engineering decisions and technical trade-off log |
| [docs/specs/prompt-history.md](docs/specs/prompt-history.md) | AI prompt versions, rationale, and regression notes |
| [docs/specs/scaling-architecture.md](docs/specs/scaling-architecture.md) | Kafka + Kubernetes future-ready architecture plan |

---

## 📈 Scaling Roadmap

| Phase | What | Status |
|:-----:|:-----|:------:|
| **Phase 1 — Digital FTE MVP** | Tool-based AI agent · dual-mode event bus · worker system · CRM schema · K8s manifests | ✅ Done |
| **Phase 2 — Intelligence + Analytics** | Smart escalation · similar issue detection · event-driven analytics · agent metrics | ✅ Done |
| **Phase 3 — Multi-channel** | Gmail + WhatsApp adapters · unified customer identity · email thread continuity · channel analytics | ✅ Done |
| **Phase 4 — Full Kafka + Streaming** | `USE_KAFKA=true` · isolated worker processes · OpenAI token streaming · WebSocket real-time push | 🔜 Next |
| **Phase 5 — Kubernetes** | Apply `k8s/` manifests · HPA on Kafka lag via KEDA · multi-tenant workspaces | 🏢 Enterprise |

The event bus and worker system are already implemented — switching to Kafka requires one env var. See [docs/specs/scaling-architecture.md](docs/specs/scaling-architecture.md).

---

## 🔮 Future Features

- [ ] **RAG knowledge base** — Company docs embedded and retrieved via pgvector / Pinecone
- [ ] **WebSocket streaming** — Real-time AI token streaming to the chat UI
- [ ] **Human handoff UI** — Admin live-chat takeover for escalated conversations
- [ ] **SLA automation** — Auto-escalation on time and priority thresholds
- [ ] **Analytics charts** — Resolution time trends, CSAT scores, volume heatmaps
- [ ] **Fine-tuned model** — Domain-specific fine-tuning on resolved ticket history
- [ ] **Multi-tenant workspaces** — Workspace isolation for B2B SaaS
- [ ] **Webhook integrations** — Slack / Teams alerts on ticket events

---

## ⭐ Support & Connect

If you like this project:

- ⭐ **Star the repository** — it helps others discover the work
- 🚀 **Try the live demo** — [supportpilot-ai-digital-fte.vercel.app](https://supportpilot-ai-digital-fte.vercel.app)
- 💼 **Connect on LinkedIn** — open for job opportunities and professional connections
- 📩 **Open an issue** — [report a bug or suggest a feature](../../issues)

---

## 🤝 Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch — `git checkout -b feature/your-feature-name`
3. Make focused, well-named commits
4. Ensure the backend starts — `uvicorn main:app --reload`
5. Ensure the frontend builds — `npm run build`
6. Open a pull request against `main`

**Code conventions:**
- **Backend:** PEP 8, async/await throughout, typed function signatures
- **Frontend:** TypeScript strict mode, functional components, Tailwind only

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License — Copyright (c) 2026 Zohair
```

---

<div align="center">

**Built with** &nbsp; FastAPI · Next.js · OpenAI · PostgreSQL · Vercel · Hugging Face

<br/>

*If this project impressed you, a ⭐ star goes a long way — thank you!*

</div>
