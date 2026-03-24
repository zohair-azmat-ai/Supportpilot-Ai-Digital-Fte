"""SupportPilot AI — FastAPI application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_db
from app.events.bus import get_event_bus
from app.utils.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown events."""
    logger.info(
        "Starting SupportPilot AI v%s [%s]",
        settings.APP_VERSION,
        settings.ENVIRONMENT,
    )
    try:
        await init_db()
        logger.info("Database initialised successfully")
    except Exception as exc:
        logger.error("Database initialisation failed: %s", exc)
        raise

    # Start event bus (InMemoryEventBus in dev, KafkaEventBus in production)
    event_bus = get_event_bus()
    try:
        await event_bus.start()
        logger.info(
            "Event bus started [mode=%s]",
            "kafka" if settings.USE_KAFKA else "in-memory",
        )
    except Exception as exc:
        logger.error("Event bus failed to start: %s", exc)
        raise

    # Start Gmail poller if enabled
    from workers.gmail_poller import gmail_poller
    if settings.GMAIL_ENABLED:
        try:
            await gmail_poller.start()
        except Exception as exc:
            logger.warning("Gmail poller failed to start (non-fatal): %s", exc)

    if settings.twilio_partial_config:
        logger.warning(
            "Twilio WhatsApp credentials are partially configured. "
            "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_WHATSAPP_FROM "
            "to enable inbound and outbound WhatsApp safely."
        )
    elif settings.twilio_configured:
        logger.info("Twilio WhatsApp integration configured")
    else:
        logger.info("Twilio WhatsApp integration not configured; webhook stays disabled")

    yield  # Application is running

    # Stop Gmail poller
    await gmail_poller.stop()

    await event_bus.stop()
    logger.info("SupportPilot AI is shutting down")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
        description=settings.APP_DESCRIPTION,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    app.include_router(api_router)

    # ------------------------------------------------------------------
    # Health / root endpoints
    # ------------------------------------------------------------------

    @app.get("/health", tags=["Health"], summary="Health check")
    async def health_check() -> dict:
        """Return service health status."""
        return {
            "status": "healthy",
            "service": settings.APP_TITLE,
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT,
        }

    @app.get("/", tags=["Root"], summary="API root")
    async def root() -> dict:
        """Return basic API information."""
        return {
            "message": f"Welcome to {settings.APP_TITLE}",
            "version": settings.APP_VERSION,
            "docs": "/docs",
            "health": "/health",
        }

    return app


app = create_app()


# ---------------------------------------------------------------------------
# Dev server entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level="info",
    )
