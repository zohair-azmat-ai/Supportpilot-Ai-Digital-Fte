# SupportPilot AI — Backend Dockerfile
# Multi-stage build: lean production image (~200 MB)
#
# Compatible with:
#   - Railway (auto-detects Dockerfile in root / backend/)
#   - Fly.io  (fly launch --dockerfile backend/Dockerfile)
#   - Hugging Face Spaces (Docker SDK — maps PORT to 7860)
#   - Any OCI-compliant container registry / host

# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools (needed for asyncpg / cryptography compilation)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application source
COPY . .

# Default port — override with $PORT env var (Hugging Face uses 7860, Railway uses dynamic)
ENV PORT=8000
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Switch to non-root user
USER appuser

EXPOSE 8000

# Hugging Face Spaces sets $PORT=7860 automatically.
# Railway / Fly.io set $PORT dynamically.
# The shell form of CMD allows $PORT to be evaluated at runtime.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
