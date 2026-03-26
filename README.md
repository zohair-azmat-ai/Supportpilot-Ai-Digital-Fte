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

[![LLM Powered](https://img.shields.io/badge/LLM_Powered-GPT--4o_mini-6d28d9?style=flat-square&logo=openai&logoColor=white)](#-features)
[![WhatsApp](https://img.shields.io/badge/WhatsApp-Integrated-25D366?style=flat-square&logo=whatsapp&logoColor=white)](#-multi-channel-design)
[![Email](https://img.shields.io/badge/Email-Integrated-0ea5e9?style=flat-square&logo=gmail&logoColor=white)](#-multi-channel-design)
[![Multi-Channel](https://img.shields.io/badge/Multi--Channel-Web_%7C_WhatsApp_%7C_Email-f59e0b?style=flat-square)](#-multi-channel-design)
[![Event Logging](https://img.shields.io/badge/Event_Logging-Enabled-10b981?style=flat-square)](#-features)
[![Analytics](https://img.shields.io/badge/Analytics-Dashboard-3b82f6?style=flat-square)](#-features)
[![Escalation Logic](https://img.shields.io/badge/Escalation-Smart_Logic-ef4444?style=flat-square)](#-features)
[![Production Ready](https://img.shields.io/badge/Architecture-Production_Style-1e293b?style=flat-square)](#-architecture)

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

## 🆕 Latest Upgrades

> Everything below is **live and shipped** — not planned, not in progress.

| Area | What was built |
|:-----|:--------------|
| **Polished SaaS UI** | Production-style frontend with separate customer and admin portals, conversations view, ticket management, and analytics dashboard |
| **Build Status Indicator** | Live system status badge in the UI header — green/yellow/red, polled every 10 seconds from `/health/build-status` |
| **WhatsApp Integration** | Full Twilio-based inbound/outbound WhatsApp support — escalation handling, follow-up suppression, duplicate webhook protection, fresh-issue-cycle reset |
| **Email Integration** | Inbound email pipeline via `POST /email/inbound`; test mode runs the full AI pipeline even when the Gmail provider is disabled; SMTP outbound when configured |
| **Real LLM Upgrade** | Moved from scripted keyword fallbacks to a structured GPT-4o-mini decision engine — replies are human-like, issue-specific, and context-aware |
| **AI Categorization** | Every message now produces `category` (billing / technical / account / general), `priority` (low / medium / high / urgent), and `urgency` (low / medium / high) |
| **Event Logging** | Structured lifecycle events: `response_generated`, `escalation_triggered`, `ticket_created` — all persisted and queryable via the metrics API |
| **Escalation Loop Fixes** | Calm follow-up suppression (`ok`, `thanks`, `got it`), duplicate escalation prevention, first-message guard, fresh-issue-cycle reset for resumed WhatsApp threads |
| **Multi-Channel Architecture** | Unified `InboundMessage` adapter pattern across Web, WhatsApp, and Email — same AI pipeline, same ticket/conversation store, same identity resolution |

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
- [🆕 Latest Upgrades](#-latest-upgrades)
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
| **LLM Decision Engine** | GPT-4o-mini structured decision engine — every reply is human-like, issue-specific, and context-aware, never generic |
| **AI Categorization** | Full triage on every message: `category` (billing / technical / account / general) + `priority` (low–urgent) + `urgency` (low–high) |
| **5-Tool AI Agent** | Strict tool order: `get_history` → `search_KB` → `create_ticket` → `[escalate]` → `send_response` |
| **Smart Escalation** | Frustration-keyword detection, repeat-issue counting, first-message guard, fresh-issue-cycle reset — eliminates false escalation loops |
| **Calm Follow-up Suppression** | `ok`, `thanks`, `got it` and similar phrases bypass the full pipeline and return a brief polite closure — no repeated escalation |
| **Event Lifecycle Logging** | Structured events: `response_generated`, `escalation_triggered`, `ticket_created` — all persisted and queryable |
| **Conversation Memory** | Context builder surfaces repeated-issue signals, failed-attempt counts, and open-ticket state before every LLM call |
| **KB Pre-fetch** | Relevant knowledge-base articles are injected into the LLM prompt before reply generation — answers reference real help content |
| **Multi-Channel** | Web ✅ · WhatsApp ✅ (Twilio) · Email ✅ (SMTP / test mode) — same AI pipeline for all three |
| **Event-Driven Bus** | InMemoryEventBus for dev · KafkaEventBus for prod — one env var to switch |
| **Agent Metrics** | Every AI call logged: intent, category, priority, urgency, confidence, tools called, response time, escalation status |
| **Build Status Indicator** | Live UI badge polls `/health/build-status` every 10 s — green (Live) / yellow (Rebuilding) / red (Offline) |

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
    subgraph FrontendLayer["  🖥️ Frontend — Next.js 14 · Vercel  "]
        direction LR
        CustomerUI["👤 Customer Portal\nChat · Tickets · Support Form"]
        AdminUI["🔧 Admin Portal\nAnalytics · Conversations · Ticket Mgmt"]
        StatusUI["🟢 Live Status Badge\n/health/build-status · 10s poll"]
    end

    subgraph ChannelLayer["  📡 Inbound Channels  "]
        direction LR
        WebCh["🌐 Web Chat\n/conversations/{id}/messages"]
        WACh["💬 WhatsApp\nTwilio · /channels/whatsapp/inbound"]
        EmailCh["✉️ Email\nSMTP + test mode · /email/inbound"]
    end

    subgraph BackendLayer["  ⚡ FastAPI Backend — Hugging Face Spaces  "]
        direction TB
        Routes["🔀 Route Handlers\n/auth · /conversations · /tickets · /admin · /channels · /health"]
        Pipeline["⚙️ Support Pipeline\nidentity resolution · conversation resume · message store"]
        EventLog["📋 Event Logger\nresponse_generated · escalation_triggered · ticket_created"]
    end

    subgraph AILayer["  🤖 AI Layer — GPT-4o-mini  "]
        direction TB
        CtxBuilder["🔍 Context Builder\nrepeated issue · failed attempts · open ticket · cross-session"]
        KBFetch["📚 KB Pre-fetch\nrelevant articles injected before LLM call"]
        DecisionEng["🧠 Decision Engine\nLLM structured reply · category · priority · urgency · escalate"]
        EscEngine["⚠️ Escalation Engine\nfrustration detection · first-message guard\ncalm follow-up suppression · issue-cycle reset"]
        ToolLoop["🛠️ Tool Loop\nget_history → KB search → create_ticket → escalate → send_response"]
        LLM["✨ OpenAI GPT-4o-mini\nJSON mode · temp 0.55 · 750 tokens"]
    end

    subgraph DataLayer["  🗄️ Data Layer — Neon PostgreSQL  "]
        direction LR
        Repos["📦 Repositories\nUser · Customer · Conversation · Message · Ticket · KB"]
        PG[("🐘 PostgreSQL\nNeon Serverless")]
        Metrics[("📊 Metrics & Events\nagent_metrics · system_events")]
    end

    FrontendLayer -->|"HTTPS REST + JWT"| Routes
    ChannelLayer --> Routes
    Routes --> Pipeline
    Pipeline --> CtxBuilder
    CtxBuilder --> KBFetch
    KBFetch --> DecisionEng
    DecisionEng --> EscEngine
    EscEngine --> ToolLoop
    ToolLoop --> LLM
    ToolLoop --> Repos
    Pipeline --> EventLog
    Pipeline --> Repos
    EventLog --> Metrics
    Repos --> PG
    Metrics --> PG

    classDef frontendStyle fill:#4f46e5,stroke:#3730a3,stroke-width:2px,color:#fff
    classDef channelStyle fill:#0891b2,stroke:#0e7490,stroke-width:2px,color:#fff
    classDef backendStyle fill:#0369a1,stroke:#075985,stroke-width:2px,color:#fff
    classDef aiStyle fill:#6d28d9,stroke:#5b21b6,stroke-width:2px,color:#fff
    classDef llmStyle fill:#312e81,stroke:#1e1b4b,stroke-width:2px,color:#fff
    classDef dbStyle fill:#065f46,stroke:#064e3b,stroke-width:2px,color:#fff

    class CustomerUI,AdminUI,StatusUI frontendStyle
    class WebCh,WACh,EmailCh channelStyle
    class Routes,Pipeline,EventLog backendStyle
    class CtxBuilder,KBFetch,DecisionEng,EscEngine,ToolLoop aiStyle
    class LLM llmStyle
    class Repos,PG,Metrics dbStyle
```

<br/>

**Layer responsibilities:**

| Layer | Responsibility |
|:------|:---------------|
| **Frontend** | Next.js 14 SaaS UI — customer portal (chat, tickets, support form), admin portal (analytics, conversations, ticket management), live build-status badge |
| **Channels** | Three active inbound adapters — Web (REST), WhatsApp (Twilio webhook), Email (SMTP / test mode) — all normalised to `InboundMessage` before the pipeline |
| **Routes** | HTTP handling — auth, validation, response serialisation, channel dispatch |
| **Support Pipeline** | Orchestrates the full turn: identity resolution, conversation resume by `thread_id`, user message store, AI agent call, AI reply store, event logging, metrics |
| **Context Builder** | Pre-LLM: loads repeated-issue signals, failed-attempt counts, and open-ticket state from conversation history and cross-session DB records |
| **KB Pre-fetch** | Retrieves the top-3 relevant knowledge-base articles before the LLM call and injects them as a system message — reply generation references real help content |
| **Decision Engine** | Calls GPT-4o-mini in JSON mode; validates and returns a `SupportDecision` with reply, `category`, `priority`, `urgency`, `intent`, `confidence`, and `escalate` flag |
| **Escalation Engine** | Post-LLM deterministic layer — frustration-keyword detection, first-message guard, calm follow-up suppression, issue-cycle reset, hard-rule escalation (legal/security) |
| **Tool Loop** | Side-effects agent: get customer history → KB search → create ticket → escalate if needed → send response (5-tool strict sequence) |
| **Event Logger** | Persists `response_generated`, `escalation_triggered`, and `ticket_created` events to `system_events`; queryable via `/metrics/events` |
| **Repositories** | One class per entity — abstract all DB queries; `lazy="raise"` on all ORM relationships to prevent implicit N+1 loads |

---

## 📡 Multi-Channel Design

Every inbound message — regardless of origin — is normalised into a shared `InboundMessage` schema before reaching the support pipeline. The service layer never sees raw channel payloads.

| Channel | Status | Entry Point |
|:--------|:------:|:------------|
| **Web Chat** | ✅ Live | `POST /api/v1/conversations/{id}/messages` |
| **Web Support Form** | ✅ Live | `POST /api/v1/support/submit` |
| **Email** | ✅ Live (test mode + SMTP) | `POST /api/v1/email/inbound` — full AI pipeline; set `SMTP_ENABLED=true` for outbound |
| **Gmail Pub/Sub** | 🟡 Activation-ready | `POST /api/v1/channels/email/inbound` — set `GMAIL_ENABLED=true` + credentials |
| **WhatsApp** | ✅ Live via Twilio | `POST /api/v1/channels/whatsapp/inbound` — set Twilio credentials and webhook |

**Unified customer identity across channels:**

- Same email on web and Gmail → one `Customer` record, shared support history
- Same phone on WhatsApp → linked via `CustomerIdentifier(channel='whatsapp')`
- AI context builder surfaces cross-channel history to the agent on every request
- Multi-channel activity detected automatically — agent informed when customer contacts from multiple channels

**Email thread continuity:**

- Gmail `thread_id` stored on the `Conversation` record
- Replies in the same Gmail thread resume the same conversation in SupportPilot
- WhatsApp sessions keyed on sender phone — one active conversation per sender

**Email integration — two modes:**

- `POST /api/v1/email/inbound` — generic JSON endpoint; runs the full AI pipeline and returns the generated reply. Works without any provider configuration — perfect for testing and CI.
- `POST /api/v1/channels/email/inbound` — Gmail Pub/Sub webhook; requires `GMAIL_ENABLED=true`. When disabled, the webhook acknowledges silently (204) so Pub/Sub never retries.
- SMTP outbound reply is sent when `SMTP_ENABLED=true` + `SMTP_HOST` are set; otherwise the AI reply is returned in the response body only.

**WhatsApp integration — active improvements:**

- Twilio-based inbound/outbound for WhatsApp Sandbox and production numbers.
- Escalation loop fixes: calm follow-up suppression, duplicate webhook deduplication via MessageSid, fresh-issue-cycle reset for resumed threads, first-message guard against inherited state.

**Safe when credentials are absent:**

- `GMAIL_ENABLED=false` (default) — Pub/Sub webhook acknowledges with 204 silently; `/email/inbound` still works without credentials
- Missing Twilio credentials — backend starts normally; WhatsApp outbound sends are logged instead of crashing
- Partial Twilio config logs a startup warning so local/dev stays safe

**Twilio WhatsApp setup:**

1. Create a Twilio account and open WhatsApp Sandbox, or provision a production WhatsApp sender.
2. Point the inbound webhook to `https://<your-backend>/api/v1/channels/whatsapp/inbound`.
3. Optional: point the status callback to `https://<your-backend>/api/v1/channels/whatsapp/status`.
4. Set `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_WHATSAPP_FROM`.
5. For sandbox usage, the customer must join the sandbox first from Twilio's provided join code.

Sandbox vs production:
Twilio Sandbox is fastest for local/dev validation. Production WhatsApp requires Twilio/Meta approval and a real WhatsApp-enabled sender. Twilio credentials are required for real inbound and outbound WhatsApp traffic.

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
| `TWILIO_ACCOUNT_SID` | For WhatsApp | Twilio account SID | `ACxxxxxxxx...` |
| `TWILIO_AUTH_TOKEN` | For WhatsApp | Twilio auth token | `your-token` |
| `TWILIO_WHATSAPP_FROM` | For WhatsApp | WhatsApp-enabled Twilio sender | `whatsapp:+14155238886` |
| `TWILIO_WHATSAPP_STATUS_CALLBACK` | Optional | Delivery callback URL | `https://api.example.com/api/v1/channels/whatsapp/status` |

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
| `POST` | `/channels/whatsapp/inbound` | Public | Twilio WhatsApp inbound webhook |
| `POST` | `/channels/whatsapp/status` | Public | Twilio WhatsApp delivery callback |

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
| **Phase 3 — Multi-channel** | WhatsApp + Email adapters · unified customer identity · email thread continuity · channel analytics | ✅ Done |
| **Phase 4 — Advanced AI + Observability** | Real LLM decision engine · AI categorization (category/priority/urgency) · event lifecycle logging · escalation loop fixes · build status indicator · email test mode · KB pre-fetch | ✅ Done |
| **Phase 5 — Memory + Retrieval** | Conversation memory layer · similar-issue retrieval · RAG over knowledge base (pgvector) · deeper context injection | 🔜 Next |
| **Phase 6 — Orchestration + Scale** | Multi-agent reasoning · full Kafka pipeline · WebSocket streaming · Kubernetes deployment with KEDA autoscaling | 🏢 Roadmap |

The event bus and worker system are already implemented — switching to Kafka requires one env var. See [docs/specs/scaling-architecture.md](docs/specs/scaling-architecture.md).

---

## 🔮 Future Features

- [ ] **Conversation memory layer** — Persist and retrieve per-user issue history across sessions for richer context injection
- [ ] **Similar-issue retrieval** — Surface semantically related past tickets to the AI before reply generation (pgvector / Pinecone)
- [ ] **RAG knowledge base** — Company docs embedded and retrieved at query time; plugs directly into the KB pre-fetch pipeline
- [ ] **Multi-agent orchestration** — Triage agent + specialist agents (billing, technical, account) with a router deciding dispatch
- [ ] **WebSocket streaming** — Real-time GPT token streaming to the chat UI
- [ ] **Human handoff UI** — Admin live-chat takeover for escalated conversations with full context hand-off
- [ ] **Deeper observability** — Resolution time trends, CSAT scores, per-channel volume heatmaps, SLA breach alerts
- [ ] **SLA automation** — Auto-escalation when tickets breach time or priority thresholds
- [ ] **Multi-tenant workspaces** — Workspace isolation for B2B SaaS usage
- [ ] **Fine-tuned model** — Domain-specific fine-tuning on resolved ticket history for lower latency and higher accuracy

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
