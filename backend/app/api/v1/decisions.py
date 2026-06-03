"""Decision API — stub. See TDS-010 §7. Implemented in E-09."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["decisions"])


@router.post("/commodities/{commodity_id}/decisions")
async def create_decision(commodity_id: str) -> JSONResponse:
    """Stub: decision session not implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented", "commodity_id": commodity_id},
    )
