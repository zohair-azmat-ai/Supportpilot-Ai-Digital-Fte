# SupportPilot AI — Deployment Guide

This guide covers local development setup, environment configuration, and step-by-step deployment to the production stack: **Vercel** (frontend), **Railway** (backend), and **Neon** (PostgreSQL).

---

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Environment Configuration](#environment-configuration)
3. [Database Migration Steps](#database-migration-steps)
4. [Database Setup — Neon](#database-setup--neon)
5. [Backend Deployment — Railway](#backend-deployment--railway)
6. [Backend Deployment — Hugging Face Spaces](#backend-deployment--hugging-face-spaces-docker)
7. [Frontend Deployment — Vercel](#frontend-deployment--vercel)
8. [Post-Deployment Checklist](#post-deployment-checklist)
9. [Monitoring and Logging](#monitoring-and-logging)
10. [Common Issues and Solutions](#common-issues-and-solutions)

---

## Local Development Setup

### System Requirements

| Dependency | Minimum Version | Install |
|---|---|---|
| Python | 3.11+ | [python.org](https://www.python.org) |
| Node.js | 18.x+ | [nodejs.org](https://nodejs.org) |
| npm | 9.x+ | Bundled with Node.js |
| PostgreSQL | 15+ | [postgresql.org](https://www.postgresql.org) or use Docker |
| Git | 2.x+ | [git-scm.com](https://git-scm.com) |

### Clone and Bootstrap

```bash
git clone https://github.com/your-username/supportpilot-ai.git
cd supportpilot-ai
```

### Backend (FastAPI)

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate        # macOS / Linux
venv\Scripts\activate           # Windows (PowerShell: venv\Scripts\Activate.ps1)

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env — see Environment Configuration section

# Run database migrations
alembic upgrade head

# Seed sample data (optional)
python ../scripts/seed.py

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Verify the backend is running:
- API root: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Frontend (Next.js)

```bash
# From project root
cd frontend

# Install dependencies
npm install

# Create environment file
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Start development server
npm run dev
```

Verify the frontend is running:
- App: `http://localhost:3000`

---

## Environment Configuration

### Backend (`backend/.env`)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:yourpassword@localhost:5432/supportpilot

# Security
SECRET_KEY=your-very-long-random-secret-key-min-32-characters
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# CORS (comma-separated, no trailing slash)
CORS_ORIGINS=http://localhost:3000,https://your-app.vercel.app

# Environment
ENVIRONMENT=development
```

**Generating a secure SECRET_KEY:**
```bash
# Linux/macOS
openssl rand -hex 32

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

### Frontend (`frontend/.env.local`)

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

In production, this becomes your Railway backend URL:
```bash
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
```

---

## Database Migration Steps

SupportPilot uses **Alembic** for all schema changes.

### Create a New Migration

```bash
cd backend
source venv/bin/activate

# Auto-generate from model changes
alembic revision --autogenerate -m "add_new_column_to_tickets"

# Review the generated file in alembic/versions/
# Edit if needed, then apply:
alembic upgrade head
```

### Apply Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Apply a specific revision
alembic upgrade <revision_id>

# Check current version
alembic current

# View migration history
alembic history --verbose
```

### Rollback

```bash
# Roll back one step
alembic downgrade -1

# Roll back to a specific revision
alembic downgrade <revision_id>

# Roll back all migrations
alembic downgrade base
```

### Production Migrations

Never run `alembic upgrade head` against production from your local machine with a local env file. Instead:
1. SSH into your Railway instance, or
2. Set `DATABASE_URL` to the Neon production string in a temporary env and run:

```bash
DATABASE_URL="postgresql+asyncpg://..." alembic upgrade head
```

Railway can also run migrations as a pre-deploy command (see Railway section below).

---

## Database Setup — Neon

Neon provides serverless PostgreSQL with automatic scaling, branching, and connection pooling.

### Step-by-Step

1. **Create an account** at [neon.tech](https://neon.tech) (free tier available).

2. **Create a new project:**
   - Click "New Project"
   - Name it `supportpilot-ai`
   - Select the region closest to your Railway backend region
   - Click "Create Project"

3. **Get the connection string:**
   - In the project dashboard, go to "Connection Details"
   - Select "Connection string" tab
   - Copy the string — it looks like:
     ```
     postgresql://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
   - For asyncpg (required for SQLAlchemy async), modify the prefix:
     ```
     postgresql+asyncpg://user:password@ep-xxx.us-east-2.aws.neon.tech/neondb?ssl=require
     ```

4. **Set the connection string:**
   - In your local `backend/.env`: set `DATABASE_URL` to the asyncpg string
   - In Railway: add it as an environment variable (see Railway section)

5. **Run migrations against Neon:**
   ```bash
   cd backend
   source venv/bin/activate
   # Ensure DATABASE_URL in .env points to Neon
   alembic upgrade head
   ```

6. **Verify in Neon dashboard:**
   - Go to "Tables" — you should see `users`, `conversations`, `messages`, `tickets`

### Neon Branching (Optional, Recommended)

Neon supports database branching — create a `dev` branch for development and testing:
- Main branch: production data
- `dev` branch: development/staging — safe to reset at any time

To create a branch: Neon dashboard → Branches → Create Branch.

---

## Backend Deployment — Railway

Railway provides containerized deployment with automatic CI/CD from GitHub.

### Prerequisites

- Railway account at [railway.app](https://railway.app)
- Repository pushed to GitHub

### Step-by-Step

1. **Create a new project:**
   - Railway dashboard → "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize Railway and select your repository

2. **Configure the service:**
   - Railway will detect the Python project
   - Set the **Root Directory** to `backend`
   - Set the **Start Command** to:
     ```
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```

3. **Add a `Procfile`** (optional but explicit) in `backend/`:
   ```
   web: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```

4. **Set environment variables:**
   Railway dashboard → your service → Variables → Add all backend variables:

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | Your Neon asyncpg connection string |
   | `SECRET_KEY` | Generated random 32-char hex string |
   | `ALGORITHM` | `HS256` |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` |
   | `OPENAI_API_KEY` | Your OpenAI API key |
   | `OPENAI_MODEL` | `gpt-4o-mini` |
   | `CORS_ORIGINS` | Your Vercel frontend URL (added after Vercel deploy) |
   | `ENVIRONMENT` | `production` |

5. **Configure automatic migrations (optional):**
   In Railway → Service Settings → Deploy → Pre-deploy command:
   ```
   alembic upgrade head
   ```
   This runs migrations before every deploy.

6. **Deploy:**
   Railway automatically deploys on every push to your configured branch (default: `main`).
   First deploy may take 3–5 minutes.

7. **Get your backend URL:**
   Railway dashboard → your service → Domains → copy the generated URL.
   Format: `https://your-service-name.railway.app`

8. **Update CORS:**
   Once you have your Vercel URL, update `CORS_ORIGINS` in Railway to include it.

### Railway Health Check

Add a health check endpoint to `app/main.py`:
```python
@app.get("/health")
async def health_check():
    return {"status": "ok"}
```

Configure Railway health check: Settings → Healthcheck Path → `/health`.

---

## Frontend Deployment — Vercel

Vercel is the recommended host for Next.js applications, with built-in CI/CD, edge functions, and CDN.

### Prerequisites

- Vercel account at [vercel.com](https://vercel.com)
- Repository on GitHub

### Step-by-Step

1. **Import your project:**
   - Vercel dashboard → "Add New Project"
   - Select your GitHub repository
   - Click "Import"

2. **Configure project settings:**
   - **Framework Preset:** Next.js (auto-detected)
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build` (auto-detected)
   - **Output Directory:** `.next` (auto-detected)
   - **Install Command:** `npm install` (auto-detected)

3. **Add environment variables:**
   Vercel dashboard → Project → Settings → Environment Variables:

   | Variable | Value | Environments |
   |---|---|---|
   | `NEXT_PUBLIC_API_URL` | `https://your-backend.railway.app` | Production, Preview |

4. **Deploy:**
   Click "Deploy". Vercel builds and deploys — typically 1–2 minutes.

5. **Get your frontend URL:**
   Format: `https://your-project-name.vercel.app`

6. **Update CORS on Railway:**
   Add your Vercel URL to `CORS_ORIGINS` in Railway environment variables.

7. **Configure custom domain (optional):**
   Vercel → Project → Settings → Domains → Add domain.

### Preview Deployments

Vercel automatically creates preview deployments for every pull request. Each PR gets a unique URL for testing. Note that preview deployments will use the same `NEXT_PUBLIC_API_URL` as set in environment variables — configure a staging Railway deployment if needed.

---

## Post-Deployment Checklist

After deploying all services, verify the following:

### Connectivity

- [ ] Backend health check: `GET https://your-backend.railway.app/health` returns `{"status": "ok"}`
- [ ] API docs accessible: `GET https://your-backend.railway.app/docs`
- [ ] Frontend loads: `https://your-app.vercel.app`
- [ ] Frontend can reach backend: check browser Network tab for successful API calls

### Authentication

- [ ] Signup flow works end-to-end
- [ ] Login returns a valid JWT
- [ ] Protected pages redirect to login when unauthenticated
- [ ] Admin pages are inaccessible to customer-role users

### Core Features

- [ ] Web support form submits successfully
- [ ] AI response is generated and displayed
- [ ] Ticket is created on form submission
- [ ] Customer chat sends and receives AI responses
- [ ] Admin dashboard shows stats
- [ ] Admin can view and update tickets

### Database

- [ ] All 4 tables exist in Neon (check Neon dashboard → Tables)
- [ ] Migrations show `head` revision: `alembic current`
- [ ] Seed data present (if seed script was run)

### Security

- [ ] `.env` files are NOT committed to the repository
- [ ] CORS only allows the Vercel frontend origin
- [ ] `SECRET_KEY` is a strong random value (not default)
- [ ] `ENVIRONMENT=production` is set on Railway

---

## Monitoring and Logging

### Backend Logs (Railway)

- Railway dashboard → your service → Deployments → view build and runtime logs
- Structured logging via Python's `logging` module
- For production, consider integrating **Sentry** for error tracking:
  ```python
  pip install sentry-sdk[fastapi]
  sentry_sdk.init(dsn="your-sentry-dsn", traces_sample_rate=0.1)
  ```

### Frontend Logs (Vercel)

- Vercel dashboard → Project → Functions tab for API route logs
- Browser console for client-side errors
- Vercel integrates with Sentry, Datadog, and other providers via the integrations marketplace

### Database Monitoring (Neon)

- Neon dashboard → Monitoring → view query metrics, connection counts
- Enable "Autoscale" in Neon for production to handle traffic spikes
- Set up Neon alerts for high connection counts or query latency

### Recommended Monitoring Stack (Future)

| Tool | Purpose |
|---|---|
| Sentry | Error tracking (backend + frontend) |
| Uptime Kuma / BetterUptime | Uptime monitoring |
| Grafana + Railway metrics | CPU/Memory dashboards |
| Neon built-in | Query performance |

---

## Backend Deployment — Hugging Face Spaces (Docker)

Hugging Face Spaces supports arbitrary Docker containers via the **Docker SDK**. This is a free option for portfolio demos — no credit card required.

### Prerequisites

- A [Hugging Face](https://huggingface.co) account (free)
- The `backend/Dockerfile` present in this repo

### Step-by-Step

1. **Create a new Space:**
   - huggingface.co → Spaces → Create new Space
   - Name: `supportpilot-ai-backend` (or any name)
   - SDK: **Docker**
   - Visibility: **Public** (required for free tier)

2. **Push the backend directory to the Space repo:**

   Hugging Face Spaces are backed by a Git repo. You can push the backend sub-directory using `git subtree`:

   ```bash
   # From the monorepo root
   git remote add hf https://huggingface.co/spaces/<your-username>/supportpilot-ai-backend
   git subtree push --prefix=backend hf main
   ```

   Or clone the Space repo separately and copy `backend/` into it.

3. **Add environment variables as Secrets:**
   - Space Settings → Repository Secrets → Add Secret for each backend env var:

   | Secret Name | Value |
   |---|---|
   | `DATABASE_URL` | Your Neon asyncpg connection string |
   | `SECRET_KEY` | Generated 32-char hex string |
   | `ALGORITHM` | `HS256` |
   | `ACCESS_TOKEN_EXPIRE_MINUTES` | `10080` |
   | `OPENAI_API_KEY` | Your OpenAI API key |
   | `OPENAI_MODEL` | `gpt-4o-mini` |
   | `CORS_ORIGINS` | Your Vercel frontend URL |
   | `ENVIRONMENT` | `production` |
   | `USE_KAFKA` | `false` |

4. **Port mapping:**
   Hugging Face Spaces expose port **7860** by default. The `Dockerfile` CMD uses `${PORT:-8000}` — Hugging Face automatically sets `PORT=7860`, so uvicorn binds to 7860. No changes needed.

5. **Build and deploy:**
   Hugging Face builds the Docker image automatically after every push. Build logs are visible in the Space's "Logs" tab. First build takes ~3–5 minutes.

6. **Get your backend URL:**
   Format: `https://<your-username>-supportpilot-ai-backend.hf.space`

   Example: `https://johndoe-supportpilot-ai-backend.hf.space`

7. **Update CORS and frontend:**
   - Set `CORS_ORIGINS` secret to your Vercel URL.
   - Set `NEXT_PUBLIC_API_URL` in Vercel to your HF Space URL.

### Hugging Face Limitations (Free Tier)

| Limitation | Detail |
|---|---|
| **Cold starts** | Spaces may sleep after inactivity. First request may be slow. |
| **CPU only** | No GPU required for FastAPI. |
| **Disk** | Ephemeral — data written to disk is lost on restart. Use Neon for all persistence. |
| **Public** | Free Spaces are public. Secrets are still protected. |

---

## Common Issues and Solutions

### `asyncpg.exceptions.InvalidAuthorizationSpecificationError`

**Cause:** Wrong credentials in `DATABASE_URL`.
**Solution:** Verify the Neon connection string. Ensure you are using `postgresql+asyncpg://` prefix and the password is URL-encoded if it contains special characters.

---

### `CORS policy: No 'Access-Control-Allow-Origin'`

**Cause:** Backend CORS configuration does not include the frontend origin.
**Solution:** Update `CORS_ORIGINS` in Railway to include the exact Vercel URL (no trailing slash). Example: `https://supportpilot.vercel.app`.

---

### `alembic.util.exc.CommandError: Can't locate revision`

**Cause:** Migration versions are out of sync (e.g., old migration files deleted).
**Solution:**
```bash
alembic stamp head      # Mark current state as head without running migrations
alembic upgrade head    # Then run from here
```

---

### `openai.AuthenticationError: Invalid API Key`

**Cause:** `OPENAI_API_KEY` is missing or incorrect on Railway.
**Solution:** Verify the key in Railway Variables. Ensure it starts with `sk-`. Do not include quotes around the value.

---

### Next.js build error: `NEXT_PUBLIC_API_URL is not defined`

**Cause:** Environment variable not set in Vercel.
**Solution:** Add `NEXT_PUBLIC_API_URL` in Vercel → Project → Settings → Environment Variables. Redeploy after adding.

---

### Railway deploy fails: `ModuleNotFoundError`

**Cause:** `requirements.txt` is out of date or the wrong root directory is configured.
**Solution:** Ensure Railway root directory is set to `backend`. Verify `requirements.txt` is up to date by running `pip freeze > requirements.txt` locally (inside the venv).

---

### `422 Unprocessable Entity` on login/signup

**Cause:** Request body format mismatch between frontend and backend schemas.
**Solution:** Check the browser Network tab for the exact request payload. Verify it matches the Pydantic schema. Common issues: `username` vs `email` field naming.

---

### Neon connection timeouts in production

**Cause:** Neon serverless instances may cold-start after inactivity.
**Solution:**
1. Enable "Connection Pooling" in Neon dashboard.
2. Use the pooler connection string (Neon provides a separate pooler endpoint).
3. Configure SQLAlchemy pool settings:
   ```python
   create_async_engine(
       DATABASE_URL,
       pool_pre_ping=True,
       pool_recycle=300
   )
   ```
