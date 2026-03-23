# Customer Support System Specification

> Defines the intended behavior of the SupportPilot AI platform: how support interactions flow, what the AI is allowed to do, when escalation occurs, and how channels are handled.

---

## 1. System Purpose

SupportPilot AI is a 24/7 AI-powered customer support platform. It receives support requests across channels, classifies them, generates helpful responses, creates tickets, and escalates to human agents when necessary.

The AI operates as a "Digital FTE" (Full-Time Employee) — always available, consistent, and professional — while knowing its limits and handing off gracefully when a human is required.

---

## 2. Support Channels

| Channel | Status | Entry Point | Notes |
|---|---|---|---|
| Web Form | Live | `POST /support/submit` | Public, no auth required |
| Web Chat | Live | `POST /conversations/{id}/messages` | Requires customer account |
| Email (Gmail) | Planned | Gmail webhook → ingest endpoint | OAuth2, Phase 2 |
| WhatsApp | Planned | Twilio webhook → ingest endpoint | Twilio sandbox, Phase 2 |

All channels funnel into the same data model: `Conversation` → `Message` → `Ticket`.

---

## 3. Support Interaction Flow

```
Customer submits message (any channel)
        │
        ▼
Message stored (sender_type = 'user')
        │
        ▼
Conversation history loaded
        │
        ▼
AI Service called (OpenAI gpt-4o-mini)
        │
        ├── Returns: response, intent, confidence, should_escalate, escalation_reason
        │
        ▼
AI response stored (sender_type = 'ai', intent + confidence recorded)
        │
        ├── should_escalate = false → Return AI response to customer
        │
        └── should_escalate = true  → Flag conversation as 'escalated'
                                       Notify admin (future: email/Slack alert)
                                       Return AI response + escalation notice to customer
```

---

## 4. AI Behavior Rules

### 4.1 What the AI SHOULD do

- Answer general product and service questions helpfully and accurately.
- Classify the intent of every message.
- Acknowledge the customer's frustration or urgency professionally.
- Guide customers through common troubleshooting steps.
- Summarize what action is being taken (ticket created, escalated, etc.).
- Keep responses concise: typically 2–4 sentences. Use bullet points for multi-step answers.
- Maintain a professional, empathetic, and solution-focused tone at all times.

### 4.2 What the AI MUST NOT do

- Make specific promises about refund amounts, timelines, or legal outcomes.
- Share internal system details, pricing tiers, or business-sensitive information unless explicitly configured in the knowledge base.
- Diagnose medical, legal, or financial situations.
- Pretend to be a human agent if directly asked.
- Fabricate order numbers, account details, or transaction records.
- Take destructive or irreversible actions (account deletion, payment processing) — these are human-only actions.

### 4.3 Tone Guidelines

| Situation | Tone |
|---|---|
| Standard inquiry | Professional, clear, concise |
| Frustrated customer | Empathetic first, then solution-focused |
| Urgent/high-priority | Acknowledge urgency, act quickly |
| Escalation | Calm, reassuring, hand-off explained |
| Out-of-scope question | Honest about limits, offer alternatives |

---

## 5. Intent Classification

The AI must classify every message into one of the following intent categories:

| Intent | Description | Example Trigger |
|---|---|---|
| `general` | General question or inquiry | "How does this work?" |
| `technical` | Technical issue or bug report | "The app keeps crashing" |
| `billing` | Payment, subscription, invoice | "I was charged twice" |
| `account` | Account access, settings, profile | "I can't log in" |
| `complaint` | Expression of dissatisfaction | "This is unacceptable" |
| `feature_request` | Suggestion for new functionality | "Can you add dark mode?" |
| `urgent` | High-urgency, time-sensitive request | "This is down in production!" |

The AI returns a `confidence` score (0.0–1.0) alongside the intent. Low confidence (< 0.5) should trigger a clarification follow-up in the response.

---

## 6. Escalation Logic

### 6.1 Auto-escalation triggers

The AI **must** recommend escalation (`should_escalate = true`) when any of the following are detected:

| Trigger Category | Examples |
|---|---|
| Billing dispute | Unauthorized charges, refund requests over a threshold, subscription cancellation disputes |
| Legal / compliance | Mentions of legal action, GDPR data requests, regulatory complaints |
| High frustration | Profanity, explicit anger, threats to leave or escalate publicly |
| Explicit request | "I want to speak to a human", "Get me your manager" |
| Security concern | Suspected account compromise, unauthorized access reports |
| Production outage | Customer reports that a service is entirely down in their environment |
| Repeated failure | Customer reports the same issue for the third+ time |

### 6.2 Escalation behavior

When `should_escalate = true`:
1. AI response is still returned — the customer receives an acknowledgment.
2. The response must include a clear statement that a human agent will follow up.
3. Conversation status is updated to `'escalated'`.
4. The ticket priority is elevated to `'high'` or `'urgent'` as appropriate.
5. Admin dashboard surfaces escalated conversations prominently.
6. (Phase 2) Admins receive a real-time notification via email or Slack.

### 6.3 Escalation response template

> "I completely understand, and I want to make sure this gets the right attention. I've flagged your case for a senior support agent who will follow up with you shortly. Your reference number is **[ticket_id]**. We apologize for the inconvenience and appreciate your patience."

---

## 7. Ticket Creation Rules

### 7.1 Automatic ticket creation

A ticket is automatically created when:
- A customer submits the **web support form** (`POST /support/submit`).

### 7.2 Manual ticket creation

A ticket is optionally created when:
- A customer explicitly requests one during a chat conversation.
- An admin manually creates one from the dashboard.

### 7.3 Ticket defaults

| Field | Default | Notes |
|---|---|---|
| `status` | `open` | |
| `priority` | Derived from AI intent | `urgent` intent → `urgent`, `complaint` → `high`, else `medium` |
| `category` | Derived from AI intent | Maps 1:1 to intent label |
| `assigned_to` | `null` | Admin assigns manually or via future auto-routing |

### 7.4 Priority mapping

| AI Intent | Default Ticket Priority |
|---|---|
| `urgent` | `urgent` |
| `complaint` | `high` |
| `billing` | `high` |
| `technical` | `medium` |
| `account` | `medium` |
| `feature_request` | `low` |
| `general` | `low` |

---

## 8. Conversation Lifecycle

```
active → escalated → (human resolves) → closed
active → (customer resolved) → closed
active → (abandoned / timeout) → closed
```

| Status | Meaning |
|---|---|
| `active` | Ongoing conversation with the customer |
| `escalated` | Handed off to a human agent |
| `closed` | Resolved or ended |

---

## 9. Knowledge Base (Phase 2)

The AI currently operates on general knowledge and the system prompt only. In Phase 2, a knowledge base will be added:

- Company-specific FAQs stored as documents.
- Embedded with OpenAI `text-embedding-3-small`.
- Stored in pgvector (Postgres extension) or Pinecone.
- Retrieved via semantic similarity search before every AI call.
- Top-K relevant chunks injected into the system prompt as context.

This will allow the AI to answer product-specific questions accurately without hallucinating.

---

## 10. Multi-Channel Normalization

Regardless of the intake channel, all support data is normalized into the same internal schema before processing:

```python
{
  "user_id": str,          # resolved from email or auth token
  "channel": str,          # 'web' | 'email' | 'whatsapp'
  "subject": str | None,   # extracted from email subject or form field
  "message": str,          # the raw customer message
  "metadata": dict         # channel-specific fields (e.g., email headers)
}
```

Each channel adapter is responsible for this normalization before passing to `SupportService`.
