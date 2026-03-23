"""
Seed the SupportPilot knowledge base with real support articles.

Usage:
    cd backend
    source venv/bin/activate
    python scripts/seed_kb.py

Idempotent: articles are identified by title; existing articles are not duplicated.
Adds 25 articles across categories: billing, technical, account, general, feature_request.
"""

from __future__ import annotations

import asyncio
import os
import sys

# Add backend root to path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal, init_db
from app.models.knowledge_base import KnowledgeBase

ARTICLES = [
    # =========================================================================
    # BILLING
    # =========================================================================
    {
        "title": "How to update your payment method",
        "category": "billing",
        "tags": "payment, credit card, billing, update, change, visa, mastercard",
        "content": (
            "You can update your payment method at any time from your account settings.\n\n"
            "**Steps:**\n"
            "1. Log in to your SupportPilot account.\n"
            "2. Navigate to Settings → Billing → Payment Methods.\n"
            "3. Click 'Add payment method' or 'Replace current card'.\n"
            "4. Enter your new card details and click Save.\n\n"
            "Your subscription will automatically use the new card on the next billing cycle. "
            "Old payment details are removed immediately. We accept Visa, Mastercard, and "
            "American Express. PayPal support is available for annual plans."
        ),
    },
    {
        "title": "Understanding your monthly invoice",
        "category": "billing",
        "tags": "invoice, bill, receipt, charge, subscription, monthly, annual",
        "content": (
            "Your monthly invoice is generated on the same date each month (your billing date).\n\n"
            "**Invoice sections:**\n"
            "- **Plan charge**: your base subscription fee\n"
            "- **Usage overage**: additional charges if you exceeded plan limits\n"
            "- **Taxes**: VAT or sales tax where applicable\n"
            "- **Credits**: any applied promo codes or support credits\n\n"
            "Invoices are sent to the email address on your account and are also available "
            "under Settings → Billing → Invoice History. You can download PDFs of all past invoices."
        ),
    },
    {
        "title": "How to cancel your subscription",
        "category": "billing",
        "tags": "cancel, cancellation, subscription, refund, downgrade, end, terminate",
        "content": (
            "You can cancel your SupportPilot subscription at any time — no cancellation fees apply.\n\n"
            "**To cancel:**\n"
            "1. Go to Settings → Billing → Subscription.\n"
            "2. Click 'Cancel plan' and confirm.\n"
            "3. Your plan stays active until the end of the current billing period.\n"
            "4. You will receive a confirmation email.\n\n"
            "**After cancellation:**\n"
            "- Your data is retained for 30 days in read-only mode.\n"
            "- You can reactivate within 30 days to restore full access.\n"
            "- After 30 days, data is permanently deleted per our retention policy.\n\n"
            "Refunds for unused time are issued at our discretion for annual plans. "
            "Contact support for refund requests."
        ),
    },
    {
        "title": "Requesting a refund",
        "category": "billing",
        "tags": "refund, money back, charge, dispute, overcharge, billing error",
        "content": (
            "SupportPilot offers refunds on a case-by-case basis.\n\n"
            "**Eligible refund situations:**\n"
            "- Duplicate charge due to a system error\n"
            "- Charge after confirmed cancellation\n"
            "- Billing error (wrong amount)\n"
            "- First-time subscription within 14 days (Pro plan only)\n\n"
            "**How to request:**\n"
            "Submit a support ticket with subject 'Refund Request' and include:\n"
            "- Your account email\n"
            "- The charge amount and date\n"
            "- Reason for the refund request\n\n"
            "Refunds are processed within 5–10 business days. The amount is returned "
            "to the original payment method."
        ),
    },
    {
        "title": "Upgrading or downgrading your plan",
        "category": "billing",
        "tags": "upgrade, downgrade, plan, tier, pro, enterprise, free, change plan",
        "content": (
            "You can change your SupportPilot plan at any time.\n\n"
            "**Upgrading (Free → Pro or Pro → Enterprise):**\n"
            "- The new plan takes effect immediately.\n"
            "- You are charged a prorated amount for the remainder of the current billing period.\n"
            "- Your feature limits and API quotas increase instantly.\n\n"
            "**Downgrading (Enterprise → Pro or Pro → Free):**\n"
            "- The downgrade takes effect at the end of the current billing period.\n"
            "- You retain current plan features until the period ends.\n"
            "- If your current usage exceeds the lower plan's limits, you'll be prompted to "
            "reduce usage before the change takes effect.\n\n"
            "To change plan: Settings → Billing → Change Plan."
        ),
    },

    # =========================================================================
    # TECHNICAL
    # =========================================================================
    {
        "title": "API authentication and API keys",
        "category": "technical",
        "tags": "api, authentication, key, token, bearer, jwt, authorization, header",
        "content": (
            "SupportPilot uses JWT bearer tokens for API authentication.\n\n"
            "**Getting an API token:**\n"
            "1. POST /api/v1/auth/login with your email and password.\n"
            "2. The response contains an `access_token` field.\n"
            "3. Include it in all subsequent requests:\n"
            "   `Authorization: Bearer <your_token>`\n\n"
            "**Token lifetime:** 7 days by default. Re-authenticate when expired.\n\n"
            "**API keys (programmatic access):**\n"
            "Go to Settings → API → Create API Key. API keys are long-lived and "
            "suitable for server-to-server integrations. Store them securely — "
            "they are shown only once at creation time."
        ),
    },
    {
        "title": "Webhook integration setup",
        "category": "technical",
        "tags": "webhook, integration, payload, signature, endpoint, event, callback",
        "content": (
            "SupportPilot can send real-time event notifications to your application via webhooks.\n\n"
            "**Supported events:**\n"
            "- `ticket.created` — new ticket created\n"
            "- `ticket.updated` — status or priority changed\n"
            "- `conversation.escalated` — AI escalated to human\n"
            "- `message.ai_replied` — AI sent a response\n\n"
            "**Setup:**\n"
            "1. Go to Settings → Integrations → Webhooks.\n"
            "2. Add your endpoint URL (must be HTTPS).\n"
            "3. Select the events you want to receive.\n"
            "4. Copy your webhook secret for signature verification.\n\n"
            "**Signature verification:**\n"
            "Each request includes an `X-SupportPilot-Signature` header (HMAC-SHA256). "
            "Verify it against your webhook secret to prevent spoofed requests."
        ),
    },
    {
        "title": "Rate limits and quotas",
        "category": "technical",
        "tags": "rate limit, quota, throttle, 429, too many requests, api limit",
        "content": (
            "SupportPilot enforces rate limits to ensure fair use and platform stability.\n\n"
            "**Default limits (Pro plan):**\n"
            "| Endpoint | Limit |\n"
            "|---|---|\n"
            "| POST /conversations/{id}/messages | 60 requests/minute |\n"
            "| POST /support/submit | 30 requests/minute |\n"
            "| GET endpoints | 300 requests/minute |\n\n"
            "When you exceed a limit, the API returns HTTP 429 with a "
            "`Retry-After` header indicating when you can retry.\n\n"
            "**Handling 429:**\n"
            "```python\n"
            "import time\n"
            "retry_after = int(response.headers.get('Retry-After', 60))\n"
            "time.sleep(retry_after)\n"
            "```\n\n"
            "Enterprise plans have higher limits. Contact sales for custom quotas."
        ),
    },
    {
        "title": "Troubleshooting failed AI responses",
        "category": "technical",
        "tags": "ai, error, failed, fallback, timeout, openai, response, broken",
        "content": (
            "If the AI agent fails to respond or returns a generic error message, "
            "here are the most common causes:\n\n"
            "**1. OpenAI API timeout**\n"
            "The agent makes multiple tool calls to OpenAI. During high traffic periods "
            "this can exceed the timeout threshold. The system will automatically "
            "escalate the conversation to a human agent in this case.\n\n"
            "**2. AI response is generic/unhelpful**\n"
            "Try rephrasing your message with more specific details. The AI classifies "
            "intent based on keywords — specific descriptions get better matches "
            "in the knowledge base.\n\n"
            "**3. Conversation not updating**\n"
            "Hard refresh the page (Ctrl+Shift+R). If the issue persists, create a "
            "new conversation.\n\n"
            "**4. API returns 503**\n"
            "Brief maintenance window. Check our status page at status.supportpilot.ai."
        ),
    },
    {
        "title": "Setting up email integration (Gmail)",
        "category": "technical",
        "tags": "gmail, email, integration, setup, oauth, credentials, google",
        "content": (
            "SupportPilot supports inbound email via Gmail API integration.\n\n"
            "**Prerequisites:**\n"
            "- A Google Cloud project with Gmail API enabled\n"
            "- OAuth2 credentials (Client ID + Client Secret)\n\n"
            "**Setup steps:**\n"
            "1. Go to console.cloud.google.com and create a project.\n"
            "2. Enable the Gmail API under 'APIs & Services'.\n"
            "3. Create OAuth2 credentials (Desktop App type for initial auth).\n"
            "4. Download the credentials JSON.\n"
            "5. Run: `python scripts/gmail_auth.py --credentials path/to/creds.json`\n"
            "6. Complete the OAuth2 consent flow in your browser.\n"
            "7. Copy the refresh token to your .env: `GMAIL_REFRESH_TOKEN=...`\n\n"
            "**Polling vs Pub/Sub:**\n"
            "- Polling (default): set `GMAIL_POLL_INTERVAL_SECONDS=30`\n"
            "- Pub/Sub (production): configure Gmail push notifications to POST to "
            "`/api/v1/channels/email/inbound`"
        ),
    },
    {
        "title": "WhatsApp integration via Twilio",
        "category": "technical",
        "tags": "whatsapp, twilio, integration, setup, webhook, sandbox, phone number",
        "content": (
            "SupportPilot integrates with WhatsApp Business via the Twilio API.\n\n"
            "**Sandbox setup (free, for testing):**\n"
            "1. Create a Twilio account at twilio.com.\n"
            "2. Go to Messaging → Senders → WhatsApp Sandbox.\n"
            "3. Note your sandbox number (e.g., +14155238886).\n"
            "4. Set the webhook URL in Twilio Console to:\n"
            "   `https://your-backend.railway.app/api/v1/channels/whatsapp/inbound`\n"
            "5. Configure in .env:\n"
            "   ```\n"
            "   TWILIO_ENABLED=true\n"
            "   TWILIO_ACCOUNT_SID=ACxxxxxxxx\n"
            "   TWILIO_AUTH_TOKEN=xxxxxxxx\n"
            "   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886\n"
            "   ```\n\n"
            "**Production (Meta Business number):**\n"
            "Request a production number via Twilio → requires Meta Business verification. "
            "The same webhook URL and code work for both sandbox and production numbers."
        ),
    },

    # =========================================================================
    # ACCOUNT
    # =========================================================================
    {
        "title": "Resetting your password",
        "category": "account",
        "tags": "password, reset, forgot, change, login, locked, account",
        "content": (
            "If you've forgotten your password or need to change it:\n\n"
            "**Reset password (forgot):**\n"
            "1. Click 'Forgot password?' on the login page.\n"
            "2. Enter your account email address.\n"
            "3. Check your inbox for the reset link (check spam if not received).\n"
            "4. Click the link and set a new password.\n"
            "5. The link expires in 1 hour.\n\n"
            "**Change password (while logged in):**\n"
            "1. Go to Settings → Security → Change Password.\n"
            "2. Enter your current password and your new password.\n"
            "3. Click Save.\n\n"
            "**Password requirements:**\n"
            "- Minimum 8 characters\n"
            "- Must not be a common password\n"
            "- Maximum 72 characters"
        ),
    },
    {
        "title": "Managing team members and permissions",
        "category": "account",
        "tags": "team, members, invite, permissions, admin, role, access, user management",
        "content": (
            "Pro and Enterprise plans support multiple team members with role-based access.\n\n"
            "**Roles:**\n"
            "- **Admin**: full access — billing, settings, user management\n"
            "- **Agent**: can manage tickets and conversations, no billing access\n"
            "- **Viewer**: read-only access to tickets and analytics\n\n"
            "**Inviting a team member:**\n"
            "1. Go to Settings → Team.\n"
            "2. Click 'Invite member'.\n"
            "3. Enter their email and select a role.\n"
            "4. They'll receive an invitation email.\n\n"
            "**Removing access:**\n"
            "Settings → Team → click the member → 'Revoke access'. "
            "Their sessions are invalidated immediately."
        ),
    },
    {
        "title": "Two-factor authentication (2FA)",
        "category": "account",
        "tags": "2fa, mfa, two factor, security, totp, authenticator, otp",
        "content": (
            "Protect your account with two-factor authentication (2FA) using any TOTP "
            "authenticator app (Google Authenticator, Authy, 1Password, etc.).\n\n"
            "**Enabling 2FA:**\n"
            "1. Go to Settings → Security → Two-factor authentication.\n"
            "2. Click 'Enable 2FA'.\n"
            "3. Scan the QR code with your authenticator app.\n"
            "4. Enter the 6-digit code to confirm.\n"
            "5. Save your backup codes in a secure location.\n\n"
            "**Losing access:**\n"
            "If you lose your authenticator device, use one of your backup codes to sign in. "
            "If you've also lost those, contact support with your account email and "
            "we'll initiate identity verification to restore access."
        ),
    },
    {
        "title": "Deleting your account and data",
        "category": "account",
        "tags": "delete account, data deletion, gdpr, privacy, close account, remove data",
        "content": (
            "You can permanently delete your account and all associated data.\n\n"
            "**To delete your account:**\n"
            "1. Go to Settings → Account → Delete Account.\n"
            "2. Type 'DELETE' to confirm.\n"
            "3. Click the confirmation button.\n\n"
            "**What happens:**\n"
            "- Your account is scheduled for deletion.\n"
            "- All conversations, tickets, and data are permanently deleted within 30 days.\n"
            "- You receive a confirmation email.\n"
            "- Billing is cancelled immediately.\n\n"
            "**GDPR / data requests:**\n"
            "To request a data export before deletion, go to Settings → Privacy → Export Data. "
            "This generates a downloadable ZIP of all your data."
        ),
    },

    # =========================================================================
    # GENERAL
    # =========================================================================
    {
        "title": "What is SupportPilot AI?",
        "category": "general",
        "tags": "what is, overview, features, ai, digital fte, platform, product",
        "content": (
            "SupportPilot AI is an AI-powered customer support platform built around "
            "a Digital FTE (Full-Time Employee) concept — an always-on AI agent that "
            "handles customer support 24/7.\n\n"
            "**Core capabilities:**\n"
            "- **AI-powered chat**: real-time conversations with intent detection and "
            "contextual responses\n"
            "- **Multi-channel**: web, email (Gmail), and WhatsApp in a single platform\n"
            "- **Smart escalation**: detects when a human agent is needed (billing disputes, "
            "legal mentions, high frustration)\n"
            "- **Ticket management**: every interaction is tracked as a ticket\n"
            "- **Knowledge base**: searchable help articles that the AI uses to answer questions\n"
            "- **Analytics**: response times, intent breakdown, escalation rates\n\n"
            "The AI agent runs a structured 5-step workflow for every message: "
            "customer history → knowledge base search → ticket creation → "
            "(optional escalation) → response."
        ),
    },
    {
        "title": "Response time SLAs",
        "category": "general",
        "tags": "response time, sla, wait, how long, fast, slow, reply time",
        "content": (
            "SupportPilot AI responds to messages in real-time — typically under 3 seconds "
            "for web chat. Here are the expected response times by channel:\n\n"
            "| Channel | AI Response | Human Escalation |\n"
            "|---|---|---|\n"
            "| Web Chat | < 3 seconds | < 2 hours |\n"
            "| Email | < 30 seconds (polling) | < 4 hours |\n"
            "| WhatsApp | < 5 seconds | < 2 hours |\n\n"
            "**Human escalation SLAs by priority:**\n"
            "- Urgent: < 1 hour\n"
            "- High: < 4 hours\n"
            "- Medium: < 24 hours\n"
            "- Low: < 72 hours\n\n"
            "SLAs are based on business hours (9am–6pm your time zone) unless you're "
            "on the Enterprise plan, which includes 24/7 human escalation support."
        ),
    },
    {
        "title": "Supported languages",
        "category": "general",
        "tags": "language, english, multilingual, spanish, french, support language",
        "content": (
            "SupportPilot AI is primarily optimised for English.\n\n"
            "**Language support status:**\n"
            "- **English**: full support — AI responds in English\n"
            "- **Spanish, French, German, Portuguese**: partial support — the AI "
            "understands messages in these languages and responds in English. "
            "Full multi-language response support is on our roadmap.\n"
            "- **Other languages**: the AI will attempt to respond but accuracy may vary.\n\n"
            "**Tip**: For best AI performance, submit your request in English. "
            "If you need a response in another language, mention it in your message "
            "and the AI will attempt to accommodate."
        ),
    },
    {
        "title": "Privacy and data security",
        "category": "general",
        "tags": "privacy, security, data, gdpr, encryption, compliance, pii",
        "content": (
            "SupportPilot takes data privacy and security seriously.\n\n"
            "**Data handling:**\n"
            "- All data is encrypted in transit (TLS 1.3) and at rest (AES-256)\n"
            "- Conversation content is stored in your private database instance\n"
            "- We do not sell or share your data with third parties\n"
            "- OpenAI API calls use your data only to generate responses — "
            "OpenAI does not train on API data by default\n\n"
            "**Compliance:**\n"
            "- GDPR: data export and deletion available (see account settings)\n"
            "- SOC 2 Type II: in progress for Enterprise tier\n\n"
            "**Data retention:**\n"
            "- Active accounts: data retained indefinitely\n"
            "- Cancelled accounts: 30-day grace period, then permanent deletion\n"
            "- You can delete specific conversations at any time"
        ),
    },

    # =========================================================================
    # COMPLAINT / COMPLAINT HANDLING
    # =========================================================================
    {
        "title": "Escalating a complaint to a senior agent",
        "category": "complaint",
        "tags": "complaint, escalate, manager, senior, unhappy, dissatisfied, escalation",
        "content": (
            "If you're not satisfied with the AI response or initial support, "
            "you can request escalation to a human agent at any time.\n\n"
            "**To escalate:**\n"
            "- In chat: type 'I want to speak to a human' or 'escalate to agent'\n"
            "- The AI will recognise this and immediately flag the conversation\n"
            "- A human agent will follow up within the SLA timeframe for your plan\n\n"
            "**Formal complaint process:**\n"
            "For formal complaints (service failures, billing disputes, data issues):\n"
            "1. Submit a ticket with category 'Complaint' and priority 'High'\n"
            "2. Include all relevant details, dates, and screenshots\n"
            "3. You'll receive acknowledgement within 1 business day\n"
            "4. Resolution target: 5 business days for standard complaints\n\n"
            "We take all complaints seriously and use them to improve the platform."
        ),
    },
    {
        "title": "Service outage and incident reporting",
        "category": "general",
        "tags": "outage, down, incident, status, service, unavailable, maintenance",
        "content": (
            "If SupportPilot is not responding or you're experiencing service issues:\n\n"
            "**Check status:**\n"
            "Visit status.supportpilot.ai for real-time platform status and "
            "incident history.\n\n"
            "**During an outage:**\n"
            "- Historical conversations and tickets remain accessible\n"
            "- New AI responses may be unavailable\n"
            "- Conversations are automatically queued for processing when service resumes\n\n"
            "**Reporting a new issue:**\n"
            "1. Submit a support ticket with priority 'Urgent'\n"
            "2. Include: error message, browser/device info, time of first occurrence\n"
            "3. Screenshots or screen recordings help diagnosis\n\n"
            "**Maintenance windows:**\n"
            "Scheduled maintenance runs on Sundays between 02:00–04:00 UTC. "
            "We post advance notice on the status page 48 hours before planned maintenance."
        ),
    },
    # =========================================================================
    # FEATURE REQUEST
    # =========================================================================
    {
        "title": "How to submit a feature request",
        "category": "feature_request",
        "tags": "feature, request, idea, suggestion, roadmap, feedback, vote",
        "content": (
            "We love hearing product ideas from our customers!\n\n"
            "**Submit a feature request:**\n"
            "1. Use the support form with category 'Feature Request'\n"
            "2. Or email product@supportpilot.ai with subject 'Feature Idea: [description]'\n\n"
            "**What to include:**\n"
            "- The problem you're trying to solve\n"
            "- Your proposed solution\n"
            "- Why it would be valuable to you\n\n"
            "**Public roadmap:**\n"
            "Vote on and track feature requests at roadmap.supportpilot.ai. "
            "Popular requests are regularly added to our development roadmap.\n\n"
            "**Current roadmap highlights:**\n"
            "- WebSocket real-time chat streaming\n"
            "- RAG knowledge base with pgvector similarity search\n"
            "- Gmail/WhatsApp full production support\n"
            "- Slack and Teams integrations\n"
            "- Advanced analytics dashboards with charts"
        ),
    },
    {
        "title": "Integrating SupportPilot with Slack",
        "category": "feature_request",
        "tags": "slack, integration, teams, notification, alert, connect",
        "content": (
            "Native Slack integration is currently on our development roadmap.\n\n"
            "**What the integration will support:**\n"
            "- New ticket notifications in a Slack channel\n"
            "- Escalation alerts to on-call agents\n"
            "- Status update notifications (ticket resolved, etc.)\n"
            "- Slash command to query ticket status from Slack\n\n"
            "**Current workaround using webhooks:**\n"
            "You can use SupportPilot webhooks (Settings → Integrations → Webhooks) "
            "combined with a Slack Incoming Webhook to receive notifications now:\n\n"
            "```python\n"
            "# Example: Forward ticket.created events to Slack\n"
            "import httpx\n"
            "def forward_to_slack(event):\n"
            "    httpx.post(SLACK_WEBHOOK_URL, json={'text': f'New ticket: {event[\"title\"]}'})\n"
            "```\n\n"
            "Vote for this feature at roadmap.supportpilot.ai to help prioritise it."
        ),
    },
]


async def seed() -> None:
    """Seed the knowledge base with articles (idempotent)."""
    await init_db()

    async with AsyncSessionLocal() as db:
        added = 0
        skipped = 0

        for article_data in ARTICLES:
            # Check if an article with this title already exists
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.title == article_data["title"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                skipped += 1
                continue

            article = KnowledgeBase(
                title=article_data["title"],
                content=article_data["content"],
                category=article_data["category"],
                tags=article_data.get("tags"),
                is_active=True,
            )
            db.add(article)
            added += 1

        await db.commit()
        print(f"Knowledge base seeded: {added} articles added, {skipped} already existed.")
        print(f"Total articles: {added + skipped}")


if __name__ == "__main__":
    asyncio.run(seed())
