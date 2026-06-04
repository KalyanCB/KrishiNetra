"""MI snapshot cache payload — TDS-009 §8 (E-01-S09).

Partial field population until E-05 scoring and E-09 API. PostgreSQL remains
source of truth; Redis holds a denormalized projection keyed per TDS-006 §4.
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MISnapshotPayload(BaseModel):
    """Canonical MI snapshot JSON stored in Redis."""

    model_config = ConfigDict(extra="forbid")

    mi_snapshot_id: UUID
    commodity_id: str
    as_of_date: date
    registry_id: UUID
    generated_at: datetime
    snapshot_id: UUID
    snapshot_hash: str
    forecast_version_id: UUID | None = None
    horizon_summaries: list[dict[str, object]] | None = None
    forecast_confidence_30: float | None = None
    forecast_confidence_60: float | None = None
    forecast_confidence_90: float | None = None
    data_quality_snapshot_id: UUID | None = None
    overall_quality_score: float | None = None
    bullish_score: float | None = None
    bearish_score: float | None = None
    neutral_score: float | None = None
    market_regime: str | None = None
    current_price: float | None = None
    price_summary_by_region: list[dict[str, object]] | None = None
    bullish_factors: list[dict[str, object]] | None = None
    bearish_factors: list[dict[str, object]] | None = None
    supply_demand_summary: dict[str, object] | None = None
    signal_weights_version: str | None = None
    partial: bool = Field(
        default=True,
        description="True until E-05 populates scores, factors, and prices.",
    )
