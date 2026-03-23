# AI Prompt History

> Tracks the evolution of system prompts and AI instructions used in SupportPilot AI.
> Every significant prompt change should be logged here with the rationale and observed impact.

---

## Format

```
## v<N> — <Short description> [YYYY-MM-DD]
**Status:** Active | Deprecated | Experimental
**Used in:** <file path(s)>
**Changed from:** v<N-1> (or "Initial version")
**Reason for change:** What problem the previous version had.
**Key changes:** Bullet list of what changed.
**Observed behavior:** What improved or regressed.
```

---

## v1.0 — Initial system prompt [2026-03-23]

**Status:** Active

**Used in:** `backend/app/ai/prompts.py` → `SUPPORT_SYSTEM_PROMPT`

**Changed from:** Initial version

**Reason for change:** N/A — baseline implementation.

**Key design choices:**

- Establishes the AI as a professional customer support assistant named "SupportPilot AI".
- Instructs the model to return a strict JSON object with five required fields: `response`, `intent`, `confidence`, `should_escalate`, `escalation_reason`.
- Lists the seven valid intent categories: `general`, `technical`, `billing`, `account`, `complaint`, `feature_request`, `urgent`.
- Defines escalation triggers explicitly: billing disputes, legal mentions, high frustration, explicit human requests, security concerns.
- Prohibits the AI from making specific financial promises, diagnosing legal situations, or pretending to be human.
- Sets tone guidelines: professional, empathetic, concise (2–4 sentences unless steps require more).

**Observed behavior:**
- Correctly classifies common support intents.
- JSON output is consistent; `_parse_response()` fallback rarely triggered.
- Escalation fires appropriately on phrases like "I want a refund" and "speak to a manager".
- Occasionally over-escalates vague frustration ("this is frustrating") — acceptable for now, tunable via prompt in v1.1.

**Full prompt (at time of writing):**

> See `backend/app/ai/prompts.py` for the authoritative source. Summary below:

```
You are a professional customer support AI assistant for SupportPilot AI...

Always respond with a valid JSON object in this exact format:
{
  "response": "Your helpful response to the customer",
  "intent": "one of: general | technical | billing | account | complaint | feature_request | urgent",
  "confidence": 0.0-1.0,
  "should_escalate": true | false,
  "escalation_reason": "reason string or null"
}

Escalate when: billing disputes, legal mentions, explicit human request,
security concerns, high frustration, production outages.

Do NOT: make financial promises, pretend to be human, share internal data,
fabricate records.
```

---

## Planned: v1.1 — Escalation threshold tuning

**Status:** Planned

**Target file:** `backend/app/ai/prompts.py`

**Planned change:** Refine the escalation trigger language to reduce false positives on mild frustration. Add explicit examples of what should and should not trigger escalation.

**Motivation:** v1.0 occasionally escalates on neutral frustration phrases. The goal is to escalate only when the customer's message clearly indicates they are not satisfied with an AI response or requires human judgment.

**Proposed addition to prompt:**

```
Escalate ONLY when the frustration is severe (profanity, direct threats,
explicit "I want a human") or the topic is beyond AI scope (refunds,
legal, security). Do NOT escalate for mild annoyance phrases like
"this is frustrating" or "this is taking too long."
```

---

## Planned: v2.0 — RAG-enhanced prompt

**Status:** Planned (Phase 2)

**Target file:** `backend/app/ai/prompts.py` (dynamic prompt builder)

**Planned change:** Replace the static system prompt with a dynamic prompt builder that:
1. Loads the base system prompt.
2. Performs a semantic search of the knowledge base for the current query.
3. Injects the top-K relevant knowledge base chunks as context.
4. Passes the enriched prompt to OpenAI.

**Motivation:** The current AI relies entirely on pre-trained knowledge. With a RAG layer, the AI can answer product-specific questions (pricing, feature details, known bugs) without hallucinating.

**Expected structure:**

```python
def build_rag_prompt(base_prompt: str, retrieved_chunks: list[str]) -> str:
    context_block = "\n\n".join(retrieved_chunks)
    return f"{base_prompt}\n\n## Relevant Knowledge Base Context\n{context_block}"
```

---

## Planned: v2.1 — Conversation summarization prompt

**Status:** Planned (Phase 2)

**Target file:** `backend/app/ai/prompts.py` → `SUMMARIZATION_PROMPT`

**Purpose:** A separate prompt for summarizing long conversation threads into a brief handoff note for human agents. Used when escalation occurs.

**Proposed format:**

```
You are summarizing a customer support conversation for a human agent taking over.
Provide a 3–5 sentence summary covering:
1. What the customer's issue is.
2. What has already been attempted or discussed.
3. Why this is being escalated.
4. The recommended next action.
Keep it factual and concise.
```

---

## Prompt Testing Notes

When evaluating prompt changes, test against the following scenario categories:

| Scenario | Expected intent | Expected escalation |
|---|---|---|
| "My payment was declined" | `billing` | false |
| "I was charged twice — I want my money back NOW" | `billing` | true |
| "How do I reset my password?" | `account` | false |
| "I want to speak to a real person" | `general` | true |
| "Your app keeps crashing on iOS 17" | `technical` | false |
| "This is a legal matter" | `complaint` | true |
| "Can you add a bulk export feature?" | `feature_request` | false |
| "Our production system is completely down" | `urgent` | true |
| "Thanks, that worked!" | `general` | false |
| "I've reported this three times already" | `complaint` | true |

Run these manually via the API or `/docs` interface when updating prompts.
