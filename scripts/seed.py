"""
SupportPilot AI — Database Seed Script
=======================================
Creates sample data for development and demonstration purposes.

Seed data created:
  - 1 admin user
  - 2 customer users
  - 2 conversations with messages
  - 3 sample tickets

Usage:
    cd backend
    source venv/bin/activate
    python ../scripts/seed.py

    # Or from project root:
    python scripts/seed.py
"""

import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allow running from project root or scripts/ directory
# ---------------------------------------------------------------------------
project_root = Path(__file__).parent.parent
backend_path = project_root / "backend"
sys.path.insert(0, str(backend_path))

# Load .env from backend directory
env_path = backend_path / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)
    print(f"  Loaded environment from {env_path}")
else:
    print(f"  Warning: No .env file found at {env_path}")
    print("  Falling back to system environment variables.")

# ---------------------------------------------------------------------------
# Imports (after path setup)
# ---------------------------------------------------------------------------
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, text

try:
    from app.core.config import settings
    DATABASE_URL = settings.DATABASE_URL
except Exception:
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        print("\n  Error: DATABASE_URL not set. Check backend/.env or environment variables.")
        sys.exit(1)

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# Sample data definitions
# ---------------------------------------------------------------------------

ADMIN_USER = {
    "id": str(uuid.uuid4()),
    "name": "SupportPilot Admin",
    "email": "admin@supportpilot.ai",
    "password": "Admin123!",
    "role": "admin",
    "is_active": True,
}

CUSTOMER_USERS = [
    {
        "id": str(uuid.uuid4()),
        "name": "Alice Johnson",
        "email": "alice@example.com",
        "password": "Customer123!",
        "role": "customer",
        "is_active": True,
    },
    {
        "id": str(uuid.uuid4()),
        "name": "Bob Martinez",
        "email": "bob@example.com",
        "password": "Customer123!",
        "role": "customer",
        "is_active": True,
    },
]


def build_conversations_and_messages(alice_id: str, bob_id: str):
    conv1_id = str(uuid.uuid4())
    conv2_id = str(uuid.uuid4())

    conversations = [
        {
            "id": conv1_id,
            "user_id": alice_id,
            "channel": "web_form",
            "status": "active",
            "subject": "Double charge on my subscription",
        },
        {
            "id": conv2_id,
            "user_id": bob_id,
            "channel": "web",
            "status": "escalated",
            "subject": "Unable to access account after password reset",
        },
    ]

    messages = [
        # Conversation 1 — Alice billing issue
        {
            "id": str(uuid.uuid4()),
            "conversation_id": conv1_id,
            "sender_type": "customer",
            "content": (
                "Hi, I was charged twice for my Pro subscription this month. "
                "I can see two transactions of $49 on January 15th on my bank statement. "
                "Can you please refund one of them?"
            ),
            "intent": None,
            "ai_confidence": None,
            "metadata": {},
        },
        {
            "id": str(uuid.uuid4()),
            "conversation_id": conv1_id,
            "sender_type": "ai",
            "content": (
                "I'm sorry to hear you were charged twice — that's definitely not right, "
                "and I completely understand how frustrating that is. "
                "I can see a duplicate transaction on your account for January 15th. "
                "I've initiated a refund of $49 to your original payment method, "
                "which should appear within 3–5 business days. "
                "You'll receive an email confirmation shortly. "
                "Is there anything else I can help you with today?"
            ),
            "intent": "billing",
            "ai_confidence": 0.96,
            "metadata": {
                "model": "gpt-4o-mini",
                "escalated": False,
                "escalation_reason": None,
            },
        },
        {
            "id": str(uuid.uuid4()),
            "conversation_id": conv1_id,
            "sender_type": "customer",
            "content": "Thank you! That was fast. I really appreciate the quick resolution.",
            "intent": None,
            "ai_confidence": None,
            "metadata": {},
        },
        {
            "id": str(uuid.uuid4()),
            "conversation_id": conv1_id,
            "sender_type": "ai",
            "content": (
                "You're very welcome, Alice! I'm glad we could sort that out quickly. "
                "Your satisfaction is our top priority. "
                "If you ever have any other questions or concerns, don't hesitate to reach out. "
                "Have a great day!"
            ),
            "intent": "general",
            "ai_confidence": 0.91,
            "metadata": {
                "model": "gpt-4o-mini",
                "escalated": False,
                "escalation_reason": None,
            },
        },
        # Conversation 2 — Bob technical/account issue
        {
            "id": str(uuid.uuid4()),
            "conversation_id": conv2_id,
            "sender_type": "customer",
            "content": (
                "I reset my password three times now and I still cannot log in. "
                "I keep getting 'invalid credentials' even with the new password. "
                "This is the third time this week and it's affecting my work."
            ),
            "intent": None,
            "ai_confidence": None,
            "metadata": {},
        },
        {
            "id": str(uuid.uuid4()),
            "conversation_id": conv2_id,
            "sender_type": "ai",
            "content": (
                "I sincerely apologize for the ongoing frustration, Bob — "
                "having this happen three times is completely unacceptable and I understand "
                "how disruptive this is to your work. "
                "This issue requires direct investigation into your account by our technical team. "
                "I've escalated your case with high priority and assigned it to a senior support agent "
                "who will reach out to you at bob@example.com within the next 2 hours. "
                "Your ticket reference is included in this conversation."
            ),
            "intent": "technical",
            "ai_confidence": 0.88,
            "metadata": {
                "model": "gpt-4o-mini",
                "escalated": True,
                "escalation_reason": "Repeated login failure across multiple attempts; high customer frustration",
            },
        },
    ]

    return conversations, messages, conv1_id, conv2_id


def build_tickets(alice_id: str, bob_id: str, conv1_id: str, conv2_id: str):
    return [
        {
            "id": str(uuid.uuid4()),
            "user_id": alice_id,
            "conversation_id": conv1_id,
            "title": "Duplicate charge refund request — January billing",
            "description": (
                "Customer was charged twice for their Pro subscription on January 15th. "
                "Two transactions of $49 each were processed. "
                "AI issued refund confirmation; verify in payment processor."
            ),
            "category": "billing",
            "priority": "medium",
            "status": "resolved",
            "assigned_to": None,
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": bob_id,
            "conversation_id": conv2_id,
            "title": "Account login failure after repeated password resets",
            "description": (
                "Customer cannot log in despite resetting password 3+ times. "
                "Receiving 'invalid credentials' error consistently. "
                "Issue has persisted for multiple days. Escalated by AI — requires manual investigation."
            ),
            "category": "technical",
            "priority": "high",
            "status": "in_progress",
            "assigned_to": None,  # Will be set to admin ID after creation
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": alice_id,
            "conversation_id": None,
            "title": "Feature request: Dark mode for customer portal",
            "description": (
                "Customer has requested a dark mode option for the support portal. "
                "Low priority enhancement for the product backlog."
            ),
            "category": "general",
            "priority": "low",
            "status": "open",
            "assigned_to": None,
        },
    ]


# ---------------------------------------------------------------------------
# Seed execution
# ---------------------------------------------------------------------------

async def seed(session: AsyncSession) -> None:
    now = datetime.now(timezone.utc)

    print("\n  Checking for existing data...")

    # Check if admin already exists
    result = await session.execute(
        text("SELECT id FROM users WHERE email = :email"),
        {"email": ADMIN_USER["email"]},
    )
    existing = result.fetchone()
    if existing:
        print("  Admin user already exists — skipping seed to avoid duplicates.")
        print("  To re-seed: drop all tables, run 'alembic upgrade head', then re-run this script.")
        return

    print("\n  Creating users...")

    all_users = [ADMIN_USER] + CUSTOMER_USERS
    user_ids = {}

    for user_data in all_users:
        hashed_pw = pwd_context.hash(user_data["password"])
        await session.execute(
            text("""
                INSERT INTO users (id, name, email, password_hash, role, is_active, created_at, updated_at)
                VALUES (:id, :name, :email, :password_hash, :role, :is_active, :created_at, :updated_at)
            """),
            {
                "id": user_data["id"],
                "name": user_data["name"],
                "email": user_data["email"],
                "password_hash": hashed_pw,
                "role": user_data["role"],
                "is_active": user_data["is_active"],
                "created_at": now,
                "updated_at": now,
            },
        )
        user_ids[user_data["email"]] = user_data["id"]
        role_label = "[ADMIN]" if user_data["role"] == "admin" else "[customer]"
        print(f"    {role_label} {user_data['name']} <{user_data['email']}>")

    alice_id = user_ids["alice@example.com"]
    bob_id = user_ids["bob@example.com"]
    admin_id = user_ids["admin@supportpilot.ai"]

    print("\n  Creating conversations...")

    conversations, messages, conv1_id, conv2_id = build_conversations_and_messages(alice_id, bob_id)

    for conv in conversations:
        await session.execute(
            text("""
                INSERT INTO conversations (id, user_id, channel, status, subject, created_at, updated_at)
                VALUES (:id, :user_id, :channel, :status, :subject, :created_at, :updated_at)
            """),
            {
                **conv,
                "created_at": now,
                "updated_at": now,
            },
        )
        print(f"    Conversation: \"{conv['subject']}\" [{conv['channel']}] — {conv['status']}")

    print("\n  Creating messages...")

    for msg in messages:
        import json
        await session.execute(
            text("""
                INSERT INTO messages (id, conversation_id, sender_type, content, intent,
                                      ai_confidence, metadata, created_at)
                VALUES (:id, :conversation_id, :sender_type, :content, :intent,
                        :ai_confidence, :metadata, :created_at)
            """),
            {
                **msg,
                "metadata": json.dumps(msg["metadata"]),
                "created_at": now,
            },
        )

    print(f"    Created {len(messages)} messages across {len(conversations)} conversations.")

    print("\n  Creating tickets...")

    tickets = build_tickets(alice_id, bob_id, conv1_id, conv2_id)
    # Assign the escalated ticket to admin
    tickets[1]["assigned_to"] = admin_id

    for ticket in tickets:
        await session.execute(
            text("""
                INSERT INTO tickets (id, user_id, conversation_id, title, description,
                                     category, priority, status, assigned_to, created_at, updated_at)
                VALUES (:id, :user_id, :conversation_id, :title, :description,
                        :category, :priority, :status, :assigned_to, :created_at, :updated_at)
            """),
            {
                **ticket,
                "created_at": now,
                "updated_at": now,
            },
        )
        print(f"    [{ticket['priority'].upper()}] {ticket['title']} — {ticket['status']}")

    await session.commit()


async def main() -> None:
    print("=" * 60)
    print("  SupportPilot AI — Database Seed Script")
    print("=" * 60)

    if not DATABASE_URL:
        print("\n  Error: DATABASE_URL is not configured.")
        sys.exit(1)

    print(f"\n  Connecting to: {DATABASE_URL[:50]}...")

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with async_session() as session:
            await seed(session)
    except Exception as e:
        print(f"\n  Seed failed: {e}")
        raise
    finally:
        await engine.dispose()

    print("\n" + "=" * 60)
    print("  Seed completed successfully!")
    print("=" * 60)
    print("\n  Login credentials:")
    print("  ┌─────────────────────────────────────────────────┐")
    print("  │  Admin:    admin@supportpilot.ai / Admin123!    │")
    print("  │  Customer: alice@example.com    / Customer123!  │")
    print("  │  Customer: bob@example.com      / Customer123!  │")
    print("  └─────────────────────────────────────────────────┘\n")


if __name__ == "__main__":
    asyncio.run(main())
