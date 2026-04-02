"""Aggregate all v1 route modules into a single API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.channels import router as channels_router
from app.api.v1.routes.conversations import router as conversations_router
from app.api.v1.routes.messages import router as messages_router
from app.api.v1.routes.metrics import router as metrics_router
from app.api.v1.routes.tickets import router as tickets_router
from app.api.v1.routes.support import router as support_router
from app.api.v1.routes.admin import router as admin_router
from app.api.v1.routes.billing import router as billing_router
from app.api.v1.routes.ai import router as ai_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(conversations_router)
api_router.include_router(messages_router)
api_router.include_router(tickets_router)
api_router.include_router(support_router)
api_router.include_router(admin_router)
api_router.include_router(channels_router)
api_router.include_router(metrics_router)
api_router.include_router(billing_router)
api_router.include_router(ai_router)
