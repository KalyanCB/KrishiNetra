"""Commodity Registry API — stub. See TDS-010 §10. Implemented in E-02/E-09."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter(tags=["registry"])


@router.get("/commodities")
async def list_commodities() -> JSONResponse:
    """Stub: commodity registry not implemented."""
    return JSONResponse(status_code=501, content={"detail": "Not implemented"})
