"""FastAPI application shell (E-00-S03). No business logic."""

from __future__ import annotations

from fastapi import FastAPI

from backend.app.api.v1 import api_v1_router
from backend.app.logging_config import configure_logging
from backend.app.middleware.trace_id import TraceIdMiddleware


def create_app() -> FastAPI:
    """ASGI application factory."""
    configure_logging()
    application = FastAPI(
        title="KrishiNetra API",
        version="0.1.0-dev",
        description="Decision intelligence API shell (TDS-010).",
    )
    application.add_middleware(TraceIdMiddleware)

    @application.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(api_v1_router, prefix="/v1")
    return application


app = create_app()
