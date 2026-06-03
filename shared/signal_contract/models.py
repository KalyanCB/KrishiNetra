"""Structured signal contract stub (TDS-004 §3, REQ-060)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from shared.domain.enums import AgentType, CommodityType, Direction


class StructuredSignal(BaseModel):
    """Agent output conforming to TDS-004 §3 (no free text)."""

    agent_type: AgentType
    commodity_id: CommodityType = CommodityType.COTTON
    value: Decimal
    direction: Direction
    magnitude: Decimal = Field(ge=0, le=1)
    confidence: Decimal = Field(ge=0, le=1)
    as_of_timestamp: datetime
