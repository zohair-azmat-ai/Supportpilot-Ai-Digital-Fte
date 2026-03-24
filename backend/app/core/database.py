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
            await session.commit()
        except Exception:
            await session.rollback()
            raise
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
    # agent_metrics
    # =========================================================================

    # channel — which channel the interaction came from (web / email / whatsapp)
    """
    ALTER TABLE agent_metrics
        ADD COLUMN IF NOT EXISTS channel VARCHAR(50)
    """,
    """
    CREATE INDEX IF NOT EXISTS ix_agent_metrics_channel
        ON agent_metrics (channel)
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
    # messages — AI signal fields
    # =========================================================================

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
]


async def _apply_schema_patches() -> None:
    """Run all idempotent schema patches against the live database."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        for sql in _PATCHES:
            await conn.execute(text(sql.strip()))
