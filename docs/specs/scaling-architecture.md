# Scaling Architecture

> Documents the path from the current MVP to a production-grade, horizontally scalable system.
> Kafka and Kubernetes are treated as Phase 3 infrastructure — they are **not** implemented in the MVP.
> This document exists so architectural decisions are made intentionally, not reactively.

---

## Current State (Phase 1 — Implemented)

```
Browser / Mobile
      │
      │  HTTPS REST
      ▼
Next.js (Vercel)  ──────►  FastAPI (Railway, single instance)
                                    │
                          ┌─────────┴──────────────┐
                          │                        │
                   ┌──────┴──────┐          OpenAI API
                   │ EventBus    │          (GPT-4o-mini)
                   │ (Dual-mode) │          Tool-based agent
                   └──────┬──────┘
                          │
           ┌──────────────┼──────────────┐
           │USE_KAFKA=false              │USE_KAFKA=true
           │(InMemoryEventBus)           │(KafkaEventBus)
           ▼                            ▼
    Inline processing             Kafka topics:
    (synchronous,                 - webform_inbound
     same process)                - email_inbound
                                  - whatsapp_inbound
                                  - escalations
                                  - metrics
                                        │
                                  ┌─────▼──────┐
                                  │  Worker    │
                                  │  Process   │
                                  │(workers/)  │
                                  └────────────┘
                                        │
                                  PostgreSQL (Neon)
```

**What Phase 1 delivers:**
- Tool-based AI agent (5 tools, strict workflow order)
- Dual-mode event bus (InMemory for dev, Kafka for prod)
- Worker system (`workers/message_processor.py`) ready for standalone deployment
- CRM-grade DB schema (customers, knowledge_base, agent_metrics)
- Multi-channel adapter pattern (web live, email/WhatsApp scaffolded)
- Kubernetes manifests for API + worker deployments (`k8s/`)

**What scales automatically with more load:**
- Switch `USE_KAFKA=true` — no code changes needed
- Run `python -m workers.main` as a separate process (or K8s Deployment)
- Scale API pods independently from worker pods

---

## Phase 2 — Channel Activation + Real-Time (Near-term)

**When to apply:** When email and WhatsApp channels are activated, or when chat UX requires streaming AI responses.

```
Browser / Mobile / WhatsApp / Email
         │
         │  HTTPS / Webhooks
         ▼
Next.js (Vercel)  ──────►  FastAPI  ──►  WebSocket connections
                              │              (real-time AI streaming)
                    ┌─────────┴─────────┐
                    │                   │
              PostgreSQL           OpenAI Streaming API
              (Neon, primary + read replica)
```

**Changes:**
- Replace request/response AI calls with **OpenAI streaming** (`stream=True`)
- Add **WebSocket endpoint** (`/ws/conversations/{id}`) for live message delivery
- Activate **email** and **WhatsApp** channel adapters (see `backend/app/channels/`)
- Add **read replica** to Neon for admin dashboard queries (prevents OLTP contention)

**No new infrastructure required.** Still single-process FastAPI, single Neon project.

---

## Phase 3 — Async Queue + Horizontal Scaling (Growth stage)

**When to apply:** When inbound message volume exceeds single-process throughput, or when multi-channel spikes (e.g., email campaign) need workload isolation.

```
                     ┌──────────────┐
                     │  API Gateway │
                     │  (FastAPI)   │
                     └──────┬───────┘
                            │
                   ┌────────▼────────┐
                   │   Message Queue │
                   │   (Apache Kafka)│
                   └────────┬────────┘
                            │
          ┌─────────────────┼─────────────────┐
          │                 │                 │
   ┌──────▼──────┐  ┌───────▼──────┐  ┌──────▼──────┐
   │   Web       │  │   Email      │  │  WhatsApp   │
   │  Consumer   │  │  Consumer    │  │  Consumer   │
   │  (worker)   │  │  (worker)    │  │  (worker)   │
   └──────┬──────┘  └───────┬──────┘  └──────┬──────┘
          └─────────────────┼─────────────────┘
                            │
                   ┌────────▼────────┐
                   │  AI Service     │
                   │  (worker pool)  │
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │  PostgreSQL     │
                   │  (Neon / RDS)   │
                   └─────────────────┘
```

### Why Kafka here

| Problem | Kafka solution |
|---|---|
| Email/WhatsApp spikes overwhelm the API | Producers decouple ingest from processing |
| Long OpenAI calls time out under load | Workers consume at their own pace |
| One bad channel shouldn't affect others | Separate consumer groups per channel |
| Audit trail of all inbound messages | Kafka topic is an immutable log |

### Kafka topic design

| Topic | Producer | Consumer | Retention |
|---|---|---|---|
| `support.inbound.web` | Web adapter | AI worker | 7 days |
| `support.inbound.email` | Email adapter | AI worker | 7 days |
| `support.inbound.whatsapp` | WhatsApp adapter | AI worker | 7 days |
| `support.responses.outbound` | AI worker | Channel outbound workers | 7 days |
| `support.tickets.events` | Ticket service | Analytics, notifications | 30 days |

### Technology options

| Component | MVP choice | Phase 3 option |
|---|---|---|
| Queue | — (none) | Apache Kafka (Confluent Cloud) or AWS SQS |
| Workers | — (inline) | FastAPI background tasks → Celery → dedicated workers |
| Containers | Railway auto | Kubernetes (EKS / GKE) or Docker Compose + Swarm |
| Monitoring | Logs | Prometheus + Grafana or Datadog |

---

## Phase 4 — Kubernetes (Enterprise / Multi-tenant)

**When to apply:** When the platform becomes a B2B SaaS product with multiple customer workspaces, SLA guarantees, and 99.9%+ uptime requirements.

```
                     Ingress (nginx / Traefik)
                            │
            ┌───────────────┼───────────────┐
            │               │               │
       ┌────▼────┐    ┌─────▼────┐    ┌─────▼────┐
       │  API    │    │  API     │    │  API     │
       │  Pod 1  │    │  Pod 2   │    │  Pod N   │  ← HorizontalPodAutoscaler
       └────┬────┘    └─────┬────┘    └─────┬────┘
            └───────────────┼───────────────┘
                            │
                   ┌────────▼────────┐
                   │  Kafka Cluster  │
                   │  (3-broker)     │
                   └────────┬────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
       ┌────▼────┐    ┌─────▼────┐    ┌─────▼────┐
       │  AI     │    │  Email   │    │  WA      │
       │ Worker  │    │ Worker   │    │ Worker   │  ← Deployment per channel
       └────┬────┘    └─────┬────┘    └─────┬────┘
            └───────────────┼───────────────┘
                            │
                   ┌────────▼────────┐
                   │  PostgreSQL     │
                   │  (Primary + HA  │
                   │   standby)      │
                   └─────────────────┘
```

### Kubernetes components

| Component | Purpose |
|---|---|
| `Deployment` | API pods, AI workers, channel workers |
| `HorizontalPodAutoscaler` | Scale API pods on CPU/RPS metric |
| `ConfigMap` / `Secret` | Environment variables, API keys |
| `PersistentVolumeClaim` | Kafka log storage |
| `Ingress` | TLS termination, routing |
| `CronJob` | Scheduled tasks (SLA checks, digest emails) |

---

## Migration Path

The channel adapter pattern in `backend/app/channels/` is designed to support this scaling path without core rewrites:

```
Phase 1 (now)
  SupportService.submit_support_form() calls web_adapter.parse_inbound() inline

Phase 2 (streaming)
  Same adapters, but MessageService uses OpenAI streaming + WebSocket push

Phase 3 (Kafka)
  Channel webhook endpoints publish InboundMessage to Kafka topic
  AI workers consume from topic and call the same SupportService pipeline
  Channel adapters remain unchanged — just called from workers instead of routes

Phase 4 (K8s)
  Workers deployed as Kubernetes Deployments
  HPA scales AI workers based on Kafka consumer lag metric
```

The data model and service layer do **not change** between phases. Only the transport layer (HTTP → queue → K8s) evolves.

---

## Decision: Don't add Kafka/K8s to MVP

Adding Kafka and Kubernetes to the MVP would:
- Require 3-5x more infrastructure code with no user-visible benefit
- Slow down local development (Docker Compose with Kafka is heavy)
- Make the portfolio project harder to set up for reviewers
- Introduce operational complexity before product-market fit

**The right call is:** build clean, adapter-pattern code today that slides into a queue architecture later. That's what `backend/app/channels/` does — the adapters don't know (or care) whether they're called from an HTTP handler or a Kafka consumer.
