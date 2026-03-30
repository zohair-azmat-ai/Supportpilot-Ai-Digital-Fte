# SupportPilot AI — Hugging Face Spaces Dockerfile
# HF Docker Spaces require this file at the repo root and port 7860.

# ── Stage 1: dependency builder ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy backend source into /app so main.py is at /app/main.py
COPY backend/ .

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER appuser

# HF Spaces requires port 7860
EXPOSE 7860

# Entry point: backend/main.py creates the FastAPI `app` object.
# WORKDIR is /app so `main:app` resolves to /app/main.py::app
CMD uvicorn main:app --host 0.0.0.0 --port 7860 --workers 1
