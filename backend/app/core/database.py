"""Async SQLAlchemy database setup."""

from __future__ import annotations

from typing import AsyncGenerator
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# ---------------------------------------------------------------------------
# URL normalisation
# ---------------------------------------------------------------------------

# sslmode values that map to SSL=on in asyncpg terms
_SSL_MODES = {"require", "verify-ca", "verify-full"}

# Query parameters understood by libpq / psycopg2 but NOT by asyncpg.
# asyncpg raises TypeError for any unrecognised connect() keyword, so every
# param in this set is stripped before the URL reaches create_async_engine.
# sslmode is handled separately (translated → ssl=True) rather than just dropped.
_LIBPQ_ONLY_PARAMS = frozenset(
    {
        # Authentication / security
        "channel_binding",  # SCRAM channel binding — not supported by asyncpg
        "gssencmode",       # Kerberos/GSSAPI encryption mode
        "krbsrvname",       # Kerberos service name
        # SSL tunables (asyncpg uses an ssl.SSLContext object instead)
        "sslmode",          # handled separately below; listed here for documentation
        "sslcompression",   # libpq-level SSL compression toggle
        # Connection routing / pooling (PgBouncer / cloud proxy params)
        "target_session_attrs",  # read-write vs read-only preference
        "load_balance_hosts",    # client-side load balancing (libpq 16+)
        "hostaddr",              # numeric IP override for hostname
        # Misc libpq-only
        "service",      # pg_service.conf service name
        "replication",  # replication connection flag
        "connect_timeout",  # asyncpg uses its own timeout kwarg, not this
    }
)


def prepare_asyncpg_url(url: str) -> tuple[str, dict]:
    """Normalise a PostgreSQL URL for use with asyncpg.

    asyncpg rejects libpq/psycopg2 query parameters it does not recognise,
    raising ``TypeError: connect() got an unexpected keyword argument``.
    This function:

    1. Coerces ``postgresql://`` / ``postgres://`` schemes to
       ``postgresql+asyncpg://`` so callers that bypass pydantic (e.g. Alembic)
       still get the correct driver scheme.
    2. Strips all ``_LIBPQ_ONLY_PARAMS`` from the query string.
    3. Translates ``sslmode`` into ``connect_args={"ssl": True}`` when the
       value implies SSL (``require``, ``verify-ca``, ``verify-full``).
       Other sslmode values (``disable``, ``allow``, ``prefer``) → no SSL.

    Returns:
        (clean_url, connect_args) — pass both directly to
        ``create_async_engine(clean_url, connect_args=connect_args, ...)``.
    """
    # 1. Scheme coercion
    for bare in ("postgresql://", "postgres://"):
        if url.startswith(bare):
            url = "postgresql+asyncpg://" + url[len(bare):]
            break

    # 2. Parse query string
    parsed = urlparse(url)
    params = parse_qs(parsed.query, keep_blank_values=True)

    # 3. Extract sslmode before bulk-stripping so we can translate it
    sslmode_values = params.pop("sslmode", [])
    needs_ssl = bool(sslmode_values) and sslmode_values[0] in _SSL_MODES

    # 4. Strip remaining libpq-only params (sslmode already popped above)
    for param in _LIBPQ_ONLY_PARAMS - {"sslmode"}:
        params.pop(param, None)

    # 5. Rebuild clean URL
    clean_query = urlencode({k: v[0] for k, v in params.items()})
    clean_url = urlunparse(parsed._replace(query=clean_query))

    # 6. Build connect_args
    connect_args: dict = {}
    if needs_ssl:
        connect_args["ssl"] = True

    return clean_url, connect_args


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

_db_url, _connect_args = prepare_asyncpg_url(settings.DATABASE_URL)

engine = create_async_engine(
    _db_url,
    connect_args=_connect_args,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        else:
            # Only commit if no exception was raised — prevents committing a
            # transaction that is already in a failed/rolled-back state, which
            # would raise PendingRollbackError and mask the original error.
            await session.commit()
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# Init DB (create tables)
# ---------------------------------------------------------------------------

async def init_db() -> None:
    """Create all database tables and apply incremental schema patches."""
    import app.models  # noqa: F401 — registers all models with Base.metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    await _apply_schema_patches()


# ---------------------------------------------------------------------------
# Schema patches
#
# create_all() only creates tables that are entirely absent — it never alters
# existing tables.  Any column that was added to a model after the initial
# table creation must be patched in here.
#
# Every statement uses IF NOT EXISTS / DO NOTHING so that this function is
# fully idempotent: safe to run on every startup.
#
# New columns are added WITHOUT a NOT NULL constraint so that existing rows
# (which will have NULL for the new column) don't violate the constraint.
# Application-layer validation (Pydantic schemas + ORM defaults) enforces
# values for all new rows.
# ---------------------------------------------------------------------------

_PATCHES = [
    # =========================================================================
    # conversations
    # =========================================================================

    # user_id — FK to users, per-user conversation ownership
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS user_id VARCHAR(36)
        REFERENCES users(id) ON DELETE CASCADE
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_conversations_user_id
        ON conversations (user_id)
    """,

    # channel / status — enum-flavoured strings
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS channel VARCHAR(50) DEFAULT 'web'
    """,
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'active'
    """,

    # subject — nullable free-text
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS subject VARCHAR(500)
    """,

    # Timestamps — DEFAULT NOW() backfills existing rows with the patch time.
    # This is intentional: existing rows without a timestamp get a safe value
    # rather than NULL, which would violate NOT NULL at the ORM layer.
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()
    """,
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()
    """,

    # =========================================================================
    # agent_metrics — core columns added after initial table creation
    # =========================================================================

    # conversation_id — FK to conversations; the primary grouping key.
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS conversation_id VARCHAR(36)
        REFERENCES conversations(id) ON DELETE CASCADE
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_agent_metrics_conversation_id
        ON agent_metrics (conversation_id)
    """,

    # user_id — FK to users; nullable so metrics survive user deletion.
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS user_id VARCHAR(36)
        REFERENCES users(id) ON DELETE SET NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_agent_metrics_user_id
        ON agent_metrics (user_id)
    """,

    # channel — which channel the interaction came from (web / email / whatsapp)
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS channel VARCHAR(50)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_agent_metrics_channel
        ON agent_metrics (channel)
    """,

    # Core metrics fields — all nullable so existing rows are not affected.
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS intent_detected VARCHAR(100)
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS confidence_score FLOAT
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS tools_called JSONB
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS iterations INTEGER
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS response_time_ms FLOAT
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS model_used VARCHAR(100)
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS escalation_reason VARCHAR(500)
    """,

    # created_at — DEFAULT NOW() backfills existing rows.
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()
    """,

    # =========================================================================
    # tickets
    # =========================================================================

    # user_id — FK to users, ticket ownership
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS user_id VARCHAR(36)
        REFERENCES users(id) ON DELETE CASCADE
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_tickets_user_id
        ON tickets (user_id)
    """,

    # conversation_id — optional link to a conversation thread
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS conversation_id VARCHAR(36)
        REFERENCES conversations(id) ON DELETE SET NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_tickets_conversation_id
        ON tickets (conversation_id)
    """,

    # Core ticket fields — DEFAULT '' keeps NOT NULL compatible for old rows
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS title VARCHAR(500) DEFAULT ''
    """,
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS description TEXT DEFAULT ''
    """,
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'general'
    """,

    # Enum-flavoured strings
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS priority VARCHAR(50) DEFAULT 'medium'
    """,
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'open'
    """,

    # assigned_to — nullable FK (ticket may be unassigned)
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS assigned_to VARCHAR(36)
        REFERENCES users(id) ON DELETE SET NULL
    """,

    # Timestamps — same DEFAULT NOW() backfill strategy as conversations
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()
    """,
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()
    """,

    # AI-signal fields on tickets — nullable so existing rows are unaffected
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS sentiment VARCHAR(50)
    """,
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS urgency VARCHAR(50)
    """,
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS escalation_reason TEXT
    """,

    # =========================================================================
    # messages — core columns + AI signal fields
    # =========================================================================

    # conversation_id — FK to conversations; the primary grouping key.
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS conversation_id VARCHAR(36)
        REFERENCES conversations(id) ON DELETE CASCADE
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_messages_conversation_id
        ON messages (conversation_id)
    """,

    # sender_type — who sent the message: user / ai / agent.
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS sender_type VARCHAR(50)
    """,

    # content — the message body text.
    # DEFAULT '' backfills existing rows so they satisfy any NOT NULL constraint.
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS content TEXT DEFAULT ''
    """,

    # intent — AI-detected intent label (nullable; only set on AI messages).
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS intent VARCHAR(100)
    """,

    # ai_confidence — model confidence score 0-1 (nullable; AI messages only).
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS ai_confidence FLOAT
    """,

    # metadata — arbitrary JSON payload for extra context.
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS metadata JSONB
    """,

    # created_at — message timestamp; DEFAULT NOW() backfills existing rows.
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()
    """,

    # AI signal fields (sentiment / urgency / escalate).
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS sentiment VARCHAR(50)
    """,
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS urgency VARCHAR(50)
    """,
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS escalate BOOLEAN DEFAULT false
    """,

    # =========================================================================
    # agent_metrics — sentiment and urgency for analytics queries
    # =========================================================================

    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS sentiment VARCHAR(50)
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS urgency VARCHAR(50)
    """,

    # escalation engine output — level and structured cause for analytics
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS escalation_level VARCHAR(50)
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS escalation_cause VARCHAR(100)
    """,

    # similar issue detection — tracks how often repeated issues are detected
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS similar_issue_detected BOOLEAN DEFAULT false
    """,

    # kb_used — true when at least one KB article was found during the run
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS kb_used BOOLEAN DEFAULT false
    """,

    # was_escalated / ticket_created / kb_articles_found — core agent outcome fields
    # These were added to the model after the initial table creation.
    # DEFAULT values ensure existing rows are backfilled with safe values.
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS escalated BOOLEAN DEFAULT false
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS was_escalated BOOLEAN DEFAULT false
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS ticket_created BOOLEAN DEFAULT false
    """,
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS kb_articles_found INTEGER DEFAULT 0
    """,

    # routed_agent — Phase 6 multi-agent routing label ("general" / "billing" /
    # "technical" / "account").  Nullable so existing rows are unaffected.
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS routed_agent VARCHAR(50) DEFAULT 'general'
    """,

    # =========================================================================
    # conversations — channel-specific threading / session key
    # =========================================================================

    # thread_id: Gmail thread ID for email (resumes same thread across replies);
    #            sender phone for WhatsApp (session continuity per sender).
    #            NULL for web (each conversation is independent).
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS thread_id VARCHAR(500)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_conversations_thread_id
        ON conversations (thread_id)
    """,

    # customer_id — optional FK to the CRM Customer record.
    # Nullable so existing conversation rows are not broken by this patch.
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS customer_id VARCHAR(36)
        REFERENCES customers(id) ON DELETE SET NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_conversations_customer_id
        ON conversations (customer_id)
    """,

    # last_intent — intent category of the most recent AI response.
    # Nullable so existing rows are unaffected.
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS last_intent VARCHAR(100)
    """,

    # started_at / ended_at — session timing columns.
    # DEFAULT NOW() backfills existing rows with the patch time.
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ DEFAULT NOW()
    """,
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ
    """,

    # =========================================================================
    # customers — columns added after initial table creation
    # =========================================================================

    # user_id — optional FK linking a Customer to an auth User.
    # This column is the reported missing column; all patches here are
    # idempotent (IF NOT EXISTS) so they are safe to re-run on every startup.
    """
    ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS user_id VARCHAR(36)
        REFERENCES users(id) ON DELETE SET NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_customers_user_id
        ON customers (user_id)
    """,

    # company / plan / notes — nullable profile fields that may be absent
    # in databases created before these columns were added to the ORM model.
    """
    ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS company VARCHAR(255)
    """,
    """
    ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS plan VARCHAR(100)
    """,
    """
    ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS notes TEXT
    """,

    # is_active — boolean flag, default TRUE so existing rows stay active.
    """
    ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true
    """,

    # Timestamps — DEFAULT NOW() safely backfills any rows that pre-date
    # these columns being added.
    """
    ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()
    """,
    """
    ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()
    """,

    # external_id — unique external reference UUID for each customer.
    # Added as nullable first so existing rows are not rejected, then
    # backfilled with a generated value using pg's md5+random (works on
    # all Postgres versions without requiring the pgcrypto extension).
    """
    ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS external_id VARCHAR(255)
    """,
    """
    UPDATE customers
    SET external_id = md5(random()::text || clock_timestamp()::text)
    WHERE external_id IS NULL OR external_id = ''
    """,

    # account_tier — customer subscription tier; DEFAULT 'free' backfills.
    """
    ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS account_tier VARCHAR(50) DEFAULT 'free'
    """,

    # is_vip — VIP customer flag; DEFAULT false backfills existing rows.
    """
    ALTER TABLE customers
        ADD COLUMN IF NOT EXISTS is_vip BOOLEAN DEFAULT false
    """,

    # =========================================================================
    # customer_identifiers — columns added after initial table creation
    # =========================================================================

    # customer_id — FK to customers; added WITHOUT NOT NULL so existing rows
    # that pre-date this column are not rejected.  New rows always supply it.
    """
    ALTER TABLE customer_identifiers
        ADD COLUMN IF NOT EXISTS customer_id VARCHAR(36)
        REFERENCES customers(id) ON DELETE CASCADE
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_customer_identifiers_customer_id
        ON customer_identifiers (customer_id)
    """,

    # channel — the communication channel for this identifier.
    # DEFAULT 'web' safely backfills any existing rows.
    # native_enum=False in the ORM means it is stored as plain VARCHAR.
    """
    ALTER TABLE customer_identifiers
        ADD COLUMN IF NOT EXISTS channel VARCHAR(50) DEFAULT 'web'
    """,

    # value — the actual identifier string (email, phone, session token, etc.).
    # DEFAULT '' backfills existing rows; the NOT NULL constraint is enforced
    # at the application layer for all new inserts.
    """
    ALTER TABLE customer_identifiers
        ADD COLUMN IF NOT EXISTS value VARCHAR(500) DEFAULT ''
    """,

    # is_primary — marks which identifier is the canonical one for a customer.
    """
    ALTER TABLE customer_identifiers
        ADD COLUMN IF NOT EXISTS is_primary BOOLEAN DEFAULT false
    """,

    # identifier — canonical identifier string (alias of value; some code paths
    # write to this column directly).  DEFAULT '' backfills existing rows.
    """
    ALTER TABLE customer_identifiers
        ADD COLUMN IF NOT EXISTS identifier VARCHAR(500) DEFAULT ''
    """,
    """
    UPDATE customer_identifiers
    SET identifier = value
    WHERE identifier IS NULL OR identifier = ''
    """,

    # created_at — timestamp for when the identifier was added.
    """
    ALTER TABLE customer_identifiers
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()
    """,

    # =========================================================================
    # knowledge_base — columns added after initial table creation
    # =========================================================================

    # title — article heading; DEFAULT '' backfills existing rows.
    """
    ALTER TABLE knowledge_base
        ADD COLUMN IF NOT EXISTS title VARCHAR(500) DEFAULT ''
    """,

    # category — article category; DEFAULT 'general' backfills existing rows.
    """
    ALTER TABLE knowledge_base
        ADD COLUMN IF NOT EXISTS category VARCHAR(100) DEFAULT 'general'
    """,

    # tags — comma-separated keyword string for simple search (nullable).
    """
    ALTER TABLE knowledge_base
        ADD COLUMN IF NOT EXISTS tags VARCHAR(500)
    """,

    # is_active — soft-delete flag; DEFAULT true keeps existing rows visible.
    """
    ALTER TABLE knowledge_base
        ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT true
    """,

    # source_url — optional link to source documentation (nullable).
    """
    ALTER TABLE knowledge_base
        ADD COLUMN IF NOT EXISTS source_url VARCHAR(1000)
    """,

    # embedding — reserved for pgvector Phase 2 (nullable JSON).
    """
    ALTER TABLE knowledge_base
        ADD COLUMN IF NOT EXISTS embedding JSONB
    """,

    # Timestamps — DEFAULT NOW() safely backfills any pre-existing rows.
    """
    ALTER TABLE knowledge_base
        ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()
    """,
    """
    ALTER TABLE knowledge_base
        ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW()
    """,

    # =========================================================================
    # tickets — columns added after initial table creation
    # =========================================================================

    # customer_id — optional FK to CRM Customer; nullable so existing rows
    # without a linked Customer are not affected.
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS customer_id VARCHAR(36)
        REFERENCES customers(id) ON DELETE SET NULL
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_tickets_customer_id
        ON tickets (customer_id)
    """,

    # channel — communication channel the ticket originated from.
    # DEFAULT 'web' backfills existing rows.
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS channel VARCHAR(50) DEFAULT 'web'
    """,

    # subject — brief subject line for the ticket.
    # DEFAULT '' backfills existing rows.
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS subject VARCHAR(255) DEFAULT ''
    """,

    # escalated — whether the ticket has been escalated to a human agent.
    # DEFAULT false backfills existing rows safely.
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS escalated BOOLEAN DEFAULT false
    """,

    # ticket_ref — human-readable ticket reference (e.g. TKT-3F8A2C1D).
    # DEFAULT '' backfills existing rows so NOT NULL is not violated.
    """
    ALTER TABLE tickets
        ADD COLUMN IF NOT EXISTS ticket_ref VARCHAR(20) DEFAULT ''
    """,

    # messages — role and channel added after initial table creation
    # =========================================================================

    # role — logical actor for the message ('user', 'assistant', etc.).
    # DEFAULT 'user' safely backfills existing rows.
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user'
    """,

    # channel — communication channel for the message.
    # DEFAULT 'web' safely backfills existing rows.
    """
    ALTER TABLE messages
        ADD COLUMN IF NOT EXISTS channel VARCHAR(50) DEFAULT 'web'
    """,

    # =========================================================================
    # users — Phase 6 plan assignment
    # =========================================================================

    # plan_tier — SaaS billing tier for this user ("free" | "pro" | "team").
    # DEFAULT 'free' backfills all existing rows automatically; no data loss.
    """
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS plan_tier VARCHAR(50) DEFAULT 'free'
    """,

    # =========================================================================
    # users — Stripe-ready subscription fields (Phase 6 billing foundation)
    # =========================================================================

    # subscription_status — lifecycle state driven by Stripe webhooks when live.
    # Values: none | trial | active | past_due | canceled
    # DEFAULT 'none' safely backfills all existing rows.
    """
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS subscription_status VARCHAR(50) DEFAULT 'none'
    """,

    # current_period_end — end of the current billing period (from Stripe).
    # NULL until Stripe is activated; nullable so existing rows are unaffected.
    """
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS current_period_end TIMESTAMPTZ
    """,

    # =========================================================================
    # conversations — human handoff mode (Phase 6)
    # =========================================================================

    # handoff_mode — 'ai' = bot is responding; 'human' = admin has taken over.
    # DEFAULT 'ai' backfills all existing rows so no conversation appears broken.
    """
    ALTER TABLE conversations
        ADD COLUMN IF NOT EXISTS handoff_mode VARCHAR(20) DEFAULT 'ai'
    """,

    # =========================================================================
    # users — Stripe identifiers (populated on first checkout)
    # =========================================================================

    # stripe_customer_id — Stripe cus_... ID; null until user completes checkout.
    """
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_users_stripe_customer_id
        ON users (stripe_customer_id)
    """,

    # stripe_subscription_id — Stripe sub_... ID; null until subscription is active.
    """
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(100)
    """,
]


async def _apply_schema_patches() -> None:
    """Run all idempotent schema patches against the live database."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        for sql in _PATCHES:
            await conn.execute(text(sql.strip()))
