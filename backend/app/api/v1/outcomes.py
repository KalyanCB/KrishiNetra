"""Outcome API — stub. See TDS-010 §9. Implemented in E-09."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["outcomes"])


@router.post("/decisions/{session_id}/outcomes")
async def post_outcome(session_id: str) -> JSONResponse:
    """Stub: outcome capture not implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented", "session_id": session_id},
    )
