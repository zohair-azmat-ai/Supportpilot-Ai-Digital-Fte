# SupportPilot AI — Development Notes

Engineering notes for contributors, covering known issues, workarounds, and local-dev behaviour that differs from production.

---

## 1. Schema Drift Between ORM Models and Local Database

### What it is

SQLAlchemy's `create_all()` only creates tables that are entirely absent — it **never alters existing tables**. If you created the database tables at an earlier point in development (e.g. before `user_id`, `channel`, or `status` columns were added to the ORM models), those columns will not be present in your local DB and the backend will raise errors like:

```
sqlalchemy.exc.ProgrammingError: column conversations.user_id does not exist
sqlalchemy.exc.ProgrammingError: column tickets.created_at does not exist
```

### Fix: Idempotent startup patches

`backend/app/core/database.py` contains a `_apply_schema_patches()` function that runs **on every startup** via `init_db()`. Every patch uses `ALTER TABLE … ADD COLUMN IF NOT EXISTS`, so it is safe to run repeatedly.

Patches currently cover:

**`conversations` table:**
- `user_id` VARCHAR(36) → FK to `users(id)` ON DELETE CASCADE
- `channel` VARCHAR(50) DEFAULT 'web'
- `status` VARCHAR(50) DEFAULT 'active'
- `subject` VARCHAR(500) nullable
- `created_at` TIMESTAMPTZ DEFAULT NOW()
- `updated_at` TIMESTAMPTZ DEFAULT NOW()

**`tickets` table:**
- `user_id` VARCHAR(36) → FK to `users(id)` ON DELETE CASCADE
- `conversation_id` VARCHAR(36) → FK to `conversations(id)` ON DELETE SET NULL
- `title` VARCHAR(500) DEFAULT ''
- `description` TEXT DEFAULT ''
- `category` VARCHAR(100) DEFAULT 'general'
- `priority` VARCHAR(50) DEFAULT 'medium'
- `status` VARCHAR(50) DEFAULT 'open'
- `assigned_to` VARCHAR(36) → FK to `users(id)` ON DELETE SET NULL
- `created_at` TIMESTAMPTZ DEFAULT NOW()
- `updated_at` TIMESTAMPTZ DEFAULT NOW()

### When does this matter?

- **Local development only** — if your local DB was created from an old model snapshot.
- **Neon / production** — Alembic migrations handle all schema changes correctly. The startup patches are a safety net, not a replacement for migrations.
- **Fresh setup** — `create_all()` creates all columns from scratch; no patches needed.

### Long-term fix

Generate a proper Alembic migration for each added column:

```bash
cd backend
source venv/bin/activate
alembic revision --autogenerate -m "add_missing_columns_to_conversations_and_tickets"
alembic upgrade head
```

Review the auto-generated file in `alembic/versions/` before applying.

---

## 2. bcrypt / passlib Compatibility

### What changed

`passlib==1.7.4` is **incompatible with `bcrypt >= 4.0`**. bcrypt 4.0 removed the `__about__` module that passlib probes at import time, causing:

```
ValueError: password cannot be longer than 72 bytes
```

even for short passwords (the error surfaces from passlib's bcrypt backend initialisation, not from actual password length).

### Current approach

`passlib` has been removed entirely. The backend now uses `bcrypt==4.2.1` directly:

```python
# backend/app/core/security.py
import bcrypt as _bcrypt

def hash_password(password: str) -> str:
    pw = password.encode("utf-8")[:72]
    return _bcrypt.hashpw(pw, _bcrypt.gensalt(rounds=12)).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    pw = plain.encode("utf-8")[:72]
    return _bcrypt.checkpw(pw, hashed.encode("utf-8"))
```

Do **not** re-add `passlib` to `requirements.txt`.

---

## 3. asyncpg URL Requirements

asyncpg (the async PostgreSQL driver) rejects libpq/psycopg2 query parameters it does not recognise. The most common issue is Neon's default connection string:

```
postgresql://user:pass@host/db?sslmode=require
```

`sslmode` is a libpq parameter — asyncpg raises `TypeError: connect() got an unexpected keyword argument 'sslmode'`.

### Current approach

`backend/app/core/database.py::prepare_asyncpg_url()` strips all known libpq-only parameters and translates `sslmode=require` → `connect_args={"ssl": True}`.

It also handles `channel_binding`, `gssencmode`, `target_session_attrs`, and several others that cloud providers sometimes inject.

### What to pass in `.env`

You can safely use the Neon connection string exactly as Neon provides it:

```bash
DATABASE_URL=postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require
```

The `ensure_asyncpg_driver` validator in `config.py` coerces `postgresql://` → `postgresql+asyncpg://`, and `prepare_asyncpg_url()` strips `sslmode` and injects `connect_args={"ssl": True}`.

---

## 4. SQLAlchemy Enum Type Mismatch

### What it is

If the database column was created as `character varying` (VARCHAR) — which is what `ADD COLUMN IF NOT EXISTS … VARCHAR(50)` produces — but the ORM declares it as a native PostgreSQL `ENUM` type, SQLAlchemy generates `$1::ticket_status` casts that fail with:

```
ProgrammingError: operator does not exist: character varying = ticket_status
```

### Fix

All named `Enum()` columns across models now use `native_enum=False`:

```python
status: Mapped[str] = mapped_column(
    Enum("open", "in_progress", "resolved", "closed", name="ticket_status", native_enum=False),
    ...
)
```

This stores values as plain `VARCHAR` and skips PostgreSQL ENUM type creation entirely. The ORM still validates against the allowed values.

Affected models: `Ticket`, `Conversation`, `User`, `Message`, `CustomerIdentifier`.

---

## 5. FastAPI 204 Response Pattern

FastAPI / Starlette asserts that 204 responses have no body. Returning `None` implicitly causes `JSONResponse(content=None)` which serialises to `null` — a 1-byte body — and raises `AssertionError`.

The correct pattern used throughout the codebase:

```python
from fastapi import APIRouter, Response, status

@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
async def delete_something(...) -> Response:
    await service.delete(...)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

Both `response_class=Response` on the decorator and `return Response(...)` in the body are required.

---

## 6. Kafka Event Bus (Local Dev)

The Kafka event bus is disabled by default in local development:

```bash
# backend/.env
USE_KAFKA=false
```

With `USE_KAFKA=false`, an `InMemoryEventBus` is used instead — no Kafka installation required. The in-memory bus processes events synchronously in the same process, which is sufficient for local development and demo purposes.

To activate Kafka:

```bash
USE_KAFKA=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

And run the worker: `python -m workers.main`

---

## 7. Seed Data

A seed script is available at `scripts/seed.py`. It creates:
- 1 admin user: `admin@supportpilot.ai` / `Admin123!`
- 3 sample customer users
- Sample tickets and conversations per customer

Run from the project root:

```bash
cd backend
source venv/bin/activate
python ../scripts/seed.py
```

> **Note:** The seed script uses `bcrypt` directly (matching the updated security module). Do not use passlib-hashed credentials with this codebase.
