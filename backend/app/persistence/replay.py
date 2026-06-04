"""TDS-006 §5 historical replay helpers — E-01-S11 contract (persistence era)."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import PriceObservationModel

# E-01-S11 AC-3 / E01_EXECUTION_PLAN §7.3 — minimum replay hash inputs documented for gate.
REPLAY_HASH_INPUT_KEYS: tuple[str, ...] = (
    "registry_id",
    "snapshot_hash",
    "formula_version",
)


def end_of_as_of_date(as_of: date) -> datetime:
    """Inclusive UTC upper bound for observation reads at a historical ``as_of_date``."""
    return datetime.combine(as_of, time(23, 59, 59, 999999), tzinfo=UTC)


def build_replay_hash_inputs(
    *,
    registry_id: UUID,
    snapshot_hash: str,
    formula_version: str,
) -> dict[str, str]:
    """Return canonical replay hash input map (TDS-006 §5 step 5 / E-01-S11 AC-3)."""
    return {
        "registry_id": str(registry_id),
        "snapshot_hash": snapshot_hash,
        "formula_version": formula_version,
    }


def list_price_observations_at_cutoff(
    session: Session,
    *,
    commodity_id: str,
    market_id: str,
    as_of: date,
) -> list[PriceObservationModel]:
    """Observations visible at ``as_of`` — ``observed_at <= end_of_as_of_date(as_of)``."""
    cutoff = end_of_as_of_date(as_of)
    stmt = (
        select(PriceObservationModel)
        .where(
            PriceObservationModel.commodity_id == commodity_id,
            PriceObservationModel.market_id == market_id,
            PriceObservationModel.observed_at <= cutoff,
        )
        .order_by(PriceObservationModel.observed_at.asc())
    )
    return list(session.scalars(stmt).all())
