"""Market Intelligence API — stub. See TDS-010 §6. Implemented in E-09."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["market-intelligence"])


@router.get("/commodities/{commodity_id}/market-intelligence")
async def get_market_intelligence(commodity_id: str) -> JSONResponse:
    """Stub: MI snapshot not implemented."""
    return JSONResponse(
        status_code=501,
        content={"detail": "Not implemented", "commodity_id": commodity_id},
    )
