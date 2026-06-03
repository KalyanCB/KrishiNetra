"""Conversation API — stub. See TDS-010 §8. Implemented in E-09."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["conversation"])


@router.post("/decisions/{session_id}/conversation")
async def post_conversation(session_id: str) -> JSONResponse:
    """Stub: explainability conversation not implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented", "session_id": session_id},
    )
