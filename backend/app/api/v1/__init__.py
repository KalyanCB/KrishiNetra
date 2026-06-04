"""API v1 routers (TDS-010). Stub handlers only — E-00-S03."""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1 import (
    conversation,
    decisions,
    market_intelligence,
    outcomes,
    registry,
)

api_v1_router = APIRouter()
api_v1_router.include_router(market_intelligence.router)
api_v1_router.include_router(decisions.router)
api_v1_router.include_router(conversation.router)
api_v1_router.include_router(outcomes.router)
api_v1_router.include_router(registry.router)
api_v1_router.include_router(registry.internal_router)
