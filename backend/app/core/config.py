"""Application configuration using pydantic-settings."""

from __future__ import annotations

from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:password@localhost:5432/supportpilot"

    # JWT / Security
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 days

    # OpenAI
    OPENAI_API_KEY: str = "sk-placeholder"
    OPENAI_MODEL: str = "gpt-4o-mini"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    # Event Bus / Kafka
    # USE_KAFKA=false (default): InMemoryEventBus — no Kafka needed, local dev works as-is
    # USE_KAFKA=true  (production): KafkaEventBus — requires a running Kafka cluster
    USE_KAFKA: bool = False
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_PREFIX: str = "supportpilot"

    # ── Gmail integration ────────────────────────────────────────────────────
    # Obtain credentials via: python scripts/gmail_auth.py
    # Required env vars to activate the Gmail channel:
    GMAIL_ENABLED: bool = False
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REFRESH_TOKEN: str = ""
    GMAIL_SENDER_ADDRESS: str = "support@yourdomain.com"
    # How often to poll Gmail for new support emails (seconds)
    GMAIL_POLL_INTERVAL_SECONDS: int = 30

    # ── Twilio / WhatsApp integration ────────────────────────────────────────
    # Create a Twilio account → WhatsApp Sandbox → set webhook to POST /api/v1/channels/whatsapp/inbound
    TWILIO_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    # Twilio sends from whatsapp:+14155238886 (sandbox) or your production number
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"

    # App
    ENVIRONMENT: str = "development"
    APP_TITLE: str = "SupportPilot AI"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = (
        "Production-ready AI-powered customer support platform backend."
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def ensure_asyncpg_driver(cls, v: str) -> str:
        """Coerce plain postgresql:// URLs to use the asyncpg driver.

        Handles the common mistake of setting DATABASE_URL=postgresql://...
        in .env without the +asyncpg scheme required by SQLAlchemy asyncio.
        """
        if isinstance(v, str):
            # Replace bare postgresql:// or postgres:// with the async variant.
            # postgresql+asyncpg:// is left unchanged.
            for prefix in ("postgresql://", "postgres://"):
                if v.startswith(prefix):
                    return "postgresql+asyncpg://" + v[len(prefix):]
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | List[str]) -> List[str]:
        """Allow comma-separated string or list for CORS origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


settings = Settings()
