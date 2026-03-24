<div align="center">

# SupportPilot AI

### A production-grade AI customer support platform — built as a Digital FTE that handles tickets, chat, escalation, and analytics 24/7

<br/>

[![Next.js](https://img.shields.io/badge/Next.js_14-000000?style=for-the-badge&logo=nextdotjs&logoColor=white)](https://nextjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)
[![Python](https://img.shields.io/badge/Python_3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![OpenAI](https://img.shields.io/badge/GPT--4o--mini-412991?style=for-the-badge&logo=openai&logoColor=white)](https://platform.openai.com)

[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Vercel](https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white)](https://vercel.com)
[![Hugging Face](https://img.shields.io/badge/Hugging_Face-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co/spaces/ZohairAzmat/supportpilot-ai-fte)
[![Neon](https://img.shields.io/badge/Neon_DB-00E5B0?style=for-the-badge&logoColor=black)](https://neon.tech)
[![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=for-the-badge)](LICENSE)

<br/>

[🚀 Live Demo](#-live-demo) &nbsp;·&nbsp; [📐 Architecture](#-architecture) &nbsp;·&nbsp; [⚡ Quick Start](#-getting-started) &nbsp;·&nbsp; [📖 API Docs](https://zohairazmat-supportpilot-ai-fte.hf.space/docs) &nbsp;·&nbsp; [🐛 Report Bug](../../issues)

</div>

---

## 🚀 Live Demo

<div align="center">

| | Link | Status |
|:---|:---|:---:|
| **🌐 Frontend** | [supportpilot-ai-digital-fte.vercel.app](https://supportpilot-ai-digital-fte.vercel.app) | ✅ Live |
| **⚡ Backend API** | [zohairazmat-supportpilot-ai-fte.hf.space](https://zohairazmat-supportpilot-ai-fte.hf.space) | ✅ Live |
| **📖 Interactive API Docs** | [.../docs](https://zohairazmat-supportpilot-ai-fte.hf.space/docs) | ✅ Live |

</div>

**Deployed on:** Vercel (Next.js) · Hugging Face Spaces (FastAPI · Docker) · Neon (PostgreSQL)

**Demo credentials:**
```
Admin portal  →  admin@supportpilot.ai  /  Admin123!
```

> **Note:** The backend runs on Hugging Face Spaces free tier — first request may take 30–60 s to wake the container.

---

## ✨ Why This Project Stands Out

This is not a tutorial project or a hackathon demo. It is a **production-style monorepo** built to the standard you would expect at a well-engineered SaaS company.

| What | Why it matters |
|:---|:---|
| 🏗️ **Full-stack, live deployment** | Frontend on Vercel, backend on HF Spaces, DB on Neon — all wired together and publicly accessible |
| 🤖 **Tool-based AI agent** | The AI runs a strict 5-tool reasoning loop (not a single prompt call) — every decision is logged, auditable, and explainable |
| 📊 **Dual portal system** | Separate customer and admin experiences with role-based auth, not just a single page |
| 🔌 **Event-driven architecture** | Dual-mode event bus — InMemoryBus for dev, KafkaEventBus for prod — switchable with one env var |
| 📡 **Multi-channel design** | Channel adapter pattern normalises Web, Gmail, and WhatsApp into the same pipeline — add a channel without touching business logic |
| 📈 **CRM-grade schema** | Full relational schema: users, customers, customer_identifiers, conversations, messages, tickets, knowledge_base, agent_metrics |
| ☸️ **Scale-ready from day one** | Kafka consumer workers and Kubernetes manifests are already in the repo for the next phase |

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
- [🤝 Contributing](#-contributing)
- [📄 License](#-license)

---

## 🎯 Features

### Customer Portal
| Feature | Description |
|:---|:---|
| **AI-Powered Chat** | Real-time conversations powered by GPT-4o-mini with intent detection, context-awareness, and smart escalation |
| **Web Support Form** | No account required — submit a request and receive an AI response with a tracked ticket in one shot |
| **Ticket Dashboard** | Track every support request with status filters (open → in-progress → resolved), priority levels, and categories |
| **Conversation History** | Full threaded message history with per-message AI confidence scores and intent labels |
| **Secure Auth** | JWT-based signup and login with role-based access control (customer / admin) |

### Admin Portal
| Feature | Description |
|:---|:---|
| **Analytics Dashboard** | Live stats — total users, open tickets, active conversations, resolution rate, escalation counts |
| **Ticket Management** | Full CRUD with inline status updates, priority management, and category routing |
| **Conversation Explorer** | Browse all conversations across channels, inspect message threads, view AI confidence and escalation flags |
| **User Management** | View all registered users, roles, account status, and activity |

### Platform & AI
| Feature | Description |
|:---|:---|
| **5-Tool AI Agent** | Strict tool execution order: `get_customer_history` → `search_knowledge_base` → `create_ticket` → `[escalate_to_human]` → `send_response` |
| **Smart Escalation** | Detects billing disputes, legal language, repeated issues, and frustration signals — escalates automatically |
| **Intent Classification** | 7 intent categories (technical, billing, account, complaint, feature_request, general, urgent) with confidence scoring |
| **Conversation Memory** | Pre-flight check detects repeated topics across message history before calling OpenAI |
| **Event-Driven Bus** | Dual-mode: InMemoryEventBus for local dev, KafkaEventBus for production (zero code change) |
| **Knowledge Base** | Keyword-searchable articles with pgvector-ready `embedding` field for Phase 2 RAG |
| **Agent Metrics** | Every AI interaction logged: intent, confidence, tools called, response time, escalation status |
| **Multi-Channel** | Web live · Gmail scaffolded · WhatsApp scaffolded — activate with credentials only |

---

## 🛠 Tech Stack

### Frontend
| Technology | Version | Purpose |
|:---|:---|:---|
| Next.js | 14 (App Router) | SSR, routing, React Server Components |
| TypeScript | 5 | End-to-end type safety |
| Tailwind CSS | 3 | Utility-first dark premium UI |
| React Hook Form + Zod | — | Type-safe form validation |
| Axios | — | API client with JWT auth interceptors |
| Lucide React | — | Consistent icon system |

### Backend
| Technology | Version | Purpose |
|:---|:---|:---|
| FastAPI | Latest | Async Python REST API |
| SQLAlchemy | 2.0 (async) | Type-safe async ORM |
| Alembic | — | Schema migrations |
| asyncpg | — | Async PostgreSQL driver |
| Pydantic | v2 | Request/response schemas and settings |
| python-jose + bcrypt | — | JWT signing + password hashing |

### AI & Data
| Technology | Purpose |
|:---|:---|
| OpenAI GPT-4o-mini | Intent detection, response generation, tool-calling agent |
| PostgreSQL (Neon) | Serverless managed Postgres with pgvector support |
| Apache Kafka | Async event processing in production (USE_KAFKA=true) |

### Deployment
| Service | What runs there |
|:---|:---|
| **Vercel** | Next.js 14 frontend (edge-optimised) |
| **Hugging Face Spaces** | FastAPI backend (Docker container) |
| **Neon** | Serverless PostgreSQL database |

---

## 📐 Architecture

```mermaid
flowchart TD
    Browser(["🌐 Browser\nNext.js 14 · Vercel"])

    subgraph BackendLayer["⚡ FastAPI Backend — Hugging Face Spaces"]
        Routes["Route Handlers\n/auth · /chat · /tickets · /admin · /support"]
        Adapters["Channel Adapters\nWeb ✅  Email 🔧  WhatsApp 🔧"]
        EventBus["Event Bus\nInMemoryBus dev  ·  KafkaBus prod"]
        Services["Services\nAuth · Chat · Tickets · Support · AI"]
    end

    subgraph AgentLayer["🤖 AI Agent — GPT-4o-mini"]
        Agent["SupportAgent\nTool-calling loop · max 8 iterations"]
        Tools["5-Tool Workflow\nhistory → KB → ticket → escalate → respond"]
        GPT["OpenAI API\nGPT-4o-mini · JSON mode · temp 0.3"]
    end

    subgraph DataLayer["🗄️ Data Layer — Neon PostgreSQL"]
        Repos["Repositories\nUser · Conv · Message · Ticket · Metrics · KB"]
        PG[("PostgreSQL\nNeon Serverless")]
        KnowledgeBase[("Knowledge Base\npgvector-ready")]
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
    Repos --> KnowledgeBase

    classDef frontendStyle fill:#6366f1,stroke:#4338ca,color:#fff
    classDef backendStyle fill:#0369a1,stroke:#075985,color:#fff
    classDef aiStyle fill:#7c3aed,stroke:#6d28d9,color:#fff
    classDef gptStyle fill:#412991,stroke:#2d1b69,color:#fff
    classDef dbStyle fill:#065f46,stroke:#047857,color:#fff

    class Browser frontendStyle
    class Routes,Adapters,EventBus,Services backendStyle
    class Agent,Tools aiStyle
    class GPT gptStyle
    class Repos,PG,KnowledgeBase dbStyle
```

**Layer responsibilities:**

| Layer | Responsibility |
|:---|:---|
| **Routes** | HTTP handling — auth, validation, response serialisation |
| **Channel Adapters** | Normalise channel-specific payloads into a shared `InboundMessage` schema |
| **Event Bus** | Decouple ingest from processing — swap InMemory→Kafka with one env var |
| **Services** | Orchestrate the pipeline — auth, ticket creation, message flow |
| **AI Agent** | Run structured tool calls, classify intent, generate responses, decide on escalation |
| **Repositories** | Abstract all database queries — one class per entity |

---

## 📡 Multi-Channel Design

Every inbound message — regardless of origin — is normalised into a shared `InboundMessage` schema before reaching the support pipeline. The service layer never sees raw channel payloads.

| Channel | Status | Entry Point |
|:---|:---:|:---|
| **Web Chat** | ✅ Live | `POST /api/v1/conversations/{id}/messages` |
| **Web Support Form** | ✅ Live | `POST /api/v1/support/submit` |
| **Gmail / Email** | 🔧 Scaffolded | `backend/app/channels/email.py` — add credentials |
| **WhatsApp** | 🔧 Scaffolded | `backend/app/channels/whatsapp.py` — add Twilio credentials |

**Adapter interface — adding a new channel requires only one file:**

```python
class BaseChannelAdapter(ABC):
    async def parse_inbound(self, payload: dict) -> InboundMessage: ...
    async def send_response(self, recipient: str, message: str) -> bool: ...

# SupportService only ever receives InboundMessage — channel-agnostic by design.
```

Activating Gmail or WhatsApp requires adding credentials to `.env` and removing the `NotImplementedError` guard. **No changes to services, agents, or repositories.**

---

## 📁 Project Structure

```
supportpilot-ai/                        ← Single production monorepo
├── README.md
├── .gitignore
│
├── frontend/                           # Next.js 14 application
│   ├── app/                            # App Router pages
│   │   ├── (auth)/                     # Login · Signup
│   │   ├── (customer)/                 # Dashboard · Chat · Tickets · Support · Settings
│   │   └── (admin)/admin/              # Overview · Tickets · Conversations · Users · Analytics
│   ├── components/
│   │   ├── ui/                         # Button, Input, Card, Badge, Modal, Spinner...
│   │   ├── layout/                     # Sidebar, Header, DashboardLayout
│   │   ├── chat/                       # ChatWindow, MessageBubble, ChatInput
│   │   ├── tickets/                    # TicketCard, TicketTable
│   │   ├── dashboard/                  # StatsCard, RecentTickets
│   │   └── forms/                      # SupportForm
│   ├── context/                        # AuthContext, ToastContext
│   ├── hooks/                          # useAuth, useConversations, useTickets
│   ├── lib/                            # api.ts, auth.ts, utils.ts
│   └── types/index.ts                  # Shared TypeScript interfaces
│
├── backend/                            # FastAPI application
│   ├── main.py                         # App entry point + lifespan
│   ├── requirements.txt
│   ├── Dockerfile                      # HF Spaces / Railway container
│   │
│   └── app/
│       ├── core/                       # config · database · security · deps
│       ├── models/                     # SQLAlchemy ORM models (8 tables)
│       ├── schemas/                    # Pydantic v2 request/response schemas
│       ├── repositories/               # Data access layer — one class per entity
│       ├── services/                   # Business logic — auth · chat · tickets · support
│       ├── channels/                   # Adapter layer — base · web · email · whatsapp
│       ├── events/                     # Event bus — topics · schemas · InMemory · Kafka
│       ├── ai/
│       │   ├── agent.py                # SupportAgent — tool-calling loop
│       │   ├── tools.py                # 5 tool definitions + ToolExecutor
│       │   ├── service.py              # AIResponse dataclass + context-aware fallback
│       │   ├── prompts.py              # System prompts
│       │   └── client.py              # AsyncOpenAI singleton
│       └── api/v1/routes/              # HTTP route handlers
│
├── workers/                            # Kafka consumer workers
│   ├── message_processor.py            # Full support pipeline worker
│   └── main.py                         # python -m workers.main
│
├── docs/                               # Architecture, API spec, DB schema, AI flow
├── scripts/                            # seed.py, init_db.sh
└── k8s/                                # Kubernetes manifests (API + worker deployments)
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
# Set DATABASE_URL, SECRET_KEY, OPENAI_API_KEY (see Environment Variables below)

# Run migrations
alembic upgrade head

# Optional: seed sample data
python ../scripts/seed.py

# Start dev server
uvicorn main:app --reload --port 8000
```

> API available at `http://localhost:8000` · Swagger UI at `http://localhost:8000/docs`

### 3. Frontend

```bash
cd frontend

npm install

# NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1  (already in .env.local.example)
cp .env.local.example .env.local

npm run dev
```

> App available at `http://localhost:3000`

### 4. Database Options

**Option A — Neon (recommended, free tier):**
1. Sign up at [neon.tech](https://neon.tech)
2. Create a project and copy the connection string
3. Set `DATABASE_URL=postgresql+asyncpg://...?sslmode=require` in `backend/.env`

**Option B — Local PostgreSQL:**
```bash
psql -U postgres -c "CREATE DATABASE supportpilot;"
# DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/supportpilot
```

### 5. One-command setup

```bash
chmod +x scripts/init_db.sh
./scripts/init_db.sh --seed
```

Handles venv creation, dependency install, migrations, and seeding in one step.

**Seed admin credentials:** `admin@supportpilot.ai` / `Admin123!`

---

## 🔐 Environment Variables

### Backend — `backend/.env`

| Variable | Required | Description | Example |
|:---|:---:|:---|:---|
| `DATABASE_URL` | ✅ | PostgreSQL async connection string | `postgresql+asyncpg://user:pass@host/db` |
| `SECRET_KEY` | ✅ | JWT signing key — `openssl rand -hex 32` | `a1b2c3...` |
| `ALGORITHM` | ✅ | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | ✅ | Token lifetime | `10080` (7 days) |
| `OPENAI_API_KEY` | ✅ | OpenAI API key | `sk-...` |
| `OPENAI_MODEL` | ✅ | Model identifier | `gpt-4o-mini` |
| `CORS_ORIGINS` | ✅ | JSON array of allowed origins | `["http://localhost:3000"]` |
| `ENVIRONMENT` | ✅ | Runtime flag | `development` or `production` |
| `USE_KAFKA` | — | Event bus mode | `false` (dev) · `true` (prod) |
| `KAFKA_BOOTSTRAP_SERVERS` | If Kafka | Kafka broker | `localhost:9092` |

### Frontend — `frontend/.env.local`

| Variable | Required | Description |
|:---|:---:|:---|
| `NEXT_PUBLIC_API_URL` | ✅ | Backend API base URL — e.g. `http://localhost:8000/api/v1` |

---

## ☁️ Deployment

### Frontend — Vercel

1. Push to GitHub
2. Import at [vercel.com/new](https://vercel.com/new) — set **Root Directory** to `frontend`
3. Add environment variable: `NEXT_PUBLIC_API_URL` → your backend URL
4. Deploy — Vercel auto-detects Next.js and builds correctly

### Backend — Hugging Face Spaces (live)

1. Create a new Space → SDK: **Docker**
2. Add all environment variables under Space Settings → **Repository Secrets**
3. Push the repo — the `Dockerfile` in `backend/` maps uvicorn to `$PORT` (default 7860 on HF)

```bash
git remote add hf https://huggingface.co/spaces/<your-username>/<space-name>
git push hf main
```

### Backend — Docker (Railway / Fly.io / any container host)

```bash
cd backend
docker build -t supportpilot-backend .
docker run -p 8000:8000 --env-file .env supportpilot-backend
```

On **Railway**: connect your GitHub repo, set root directory to `backend` — Railway auto-detects the Dockerfile.

### Database — Neon

1. Sign up at [neon.tech](https://neon.tech) and create a project
2. Copy the pooled connection string
3. Set it as `DATABASE_URL` and run `alembic upgrade head`

> See [docs/deployment.md](docs/deployment.md) for the complete step-by-step walkthrough.

---

## 🔌 API Overview

All endpoints are prefixed with `/api/v1`. Full interactive docs at [`/docs`](https://zohairazmat-supportpilot-ai-fte.hf.space/docs).

| Method | Endpoint | Auth | Description |
|:---|:---|:---:|:---|
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
| `POST` | `/support/submit` | Public | Web support form → AI response + ticket |
| `GET` | `/admin/stats` | 👑 Admin | Platform statistics |
| `GET` | `/admin/tickets` | 👑 Admin | All tickets (paginated, filterable) |
| `PATCH` | `/admin/tickets/{id}` | 👑 Admin | Update any ticket |
| `GET` | `/admin/conversations` | 👑 Admin | All conversations |
| `GET` | `/admin/users` | 👑 Admin | All registered users |
| `GET` | `/metrics/overview` | 👑 Admin | AI agent performance stats |
| `GET` | `/metrics/channels` | 👑 Admin | Per-channel breakdown |
| `GET` | `/metrics/escalations` | 👑 Admin | Escalation records and rates |

> Full request/response schemas → [docs/api-spec.md](docs/api-spec.md)

---

## 📖 Documentation

| Document | What's inside |
|:---|:---|
| [docs/architecture.md](docs/architecture.md) | System design, data flow, and layer responsibilities |
| [docs/api-spec.md](docs/api-spec.md) | Full API reference with request/response examples |
| [docs/db-schema.md](docs/db-schema.md) | Database schema, entity relationships, and indexes |
| [docs/ai-flow.md](docs/ai-flow.md) | AI agent design, prompt strategy, tool execution, and escalation logic |
| [docs/deployment.md](docs/deployment.md) | Step-by-step deployment guide — Vercel + HF Spaces + Neon |
| [docs/specs/customer-support-spec.md](docs/specs/customer-support-spec.md) | AI behaviour rules, escalation triggers, channel definitions |
| [docs/specs/discovery-log.md](docs/specs/discovery-log.md) | Engineering decisions and technical trade-off log |
| [docs/specs/prompt-history.md](docs/specs/prompt-history.md) | AI prompt versions, rationale, and regression notes |
| [docs/specs/scaling-architecture.md](docs/specs/scaling-architecture.md) | Kafka + Kubernetes future-ready architecture plan |

---

## 📈 Scaling Roadmap

| Phase | What | Status |
|:---|:---|:---:|
| **Phase 1 — Digital FTE MVP** | Tool-based AI agent · event bus (dual-mode) · worker system · CRM schema · K8s manifests | ✅ Done |
| **Phase 2 — Channels + Streaming** | Activate Gmail/WhatsApp adapters · OpenAI streaming · WebSocket real-time push | 🔜 Next |
| **Phase 3 — Full Kafka** | `USE_KAFKA=true` · run `python -m workers.main` as isolated process · scale consumers | ⏳ On demand |
| **Phase 4 — Kubernetes** | Apply `k8s/` manifests · HPA on Kafka lag (KEDA) · multi-tenant workspaces | 🏢 Enterprise |

The event bus abstraction and worker system are already implemented and committed. Moving from inline to Kafka processing requires a single env var change. See [docs/specs/scaling-architecture.md](docs/specs/scaling-architecture.md).

---

## 🔮 Future Features

- [ ] **Gmail channel** — Inbound email parsing, auto-reply in thread, ticket creation
- [ ] **WhatsApp channel** — Twilio WhatsApp Business API for conversational support
- [ ] **RAG knowledge base** — Company docs embedded and retrieved via pgvector / Pinecone
- [ ] **WebSocket streaming** — Real-time AI token streaming to the chat UI
- [ ] **Human handoff UI** — Admin live-chat takeover for escalated conversations
- [ ] **SLA automation** — Auto-escalation on time and priority thresholds
- [ ] **Analytics charts** — Resolution time trends, CSAT scores, volume heatmaps
- [ ] **Fine-tuned model** — Domain-specific fine-tuning on resolved ticket history
- [ ] **Multi-tenant workspaces** — Workspace isolation for B2B SaaS
- [ ] **Webhook integrations** — Slack / Teams alerts on ticket events

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
- **Frontend:** TypeScript strict mode, functional components, Tailwind only (no inline styles)

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License — Copyright (c) 2026 Zohair
```

---

<div align="center">

Built with FastAPI · Next.js · OpenAI · Neon · Vercel · Hugging Face

⭐ **Star this repo if you found it useful**

</div>
