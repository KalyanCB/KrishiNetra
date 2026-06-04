"""Load and index futures observations for signal generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import median

from sqlalchemy.orm import Session

from backend.app.persistence.models.futures import FuturesObservationModel
from backend.app.persistence.models.observation import (
    ObservationValidationStatus,
)
from backend.app.persistence.repositories.futures import FuturesObservationRepository
from backend.app.persistence.repositories.observation import PriceObservationRepository
from backend.app.services.signals.futures.constants import ROLLING_WINDOW_DAYS

USABLE_VALIDATION_STATUSES = frozenset(
    {
        ObservationValidationStatus.VALIDATED.value,
        ObservationValidationStatus.PUBLISHED.value,
    }
)

MODAL_PRICE_TYPE = "modal"


@dataclass(frozen=True, slots=True)
class NearFarContracts:
    """Near and far KAPAS contract settles for one session."""

    as_of_date: date
    near: FuturesObservationModel
    far: FuturesObservationModel


@dataclass(frozen=True, slots=True)
class FuturesObservationSeries:
    """Indexed futures curve + OI history through as_of_date."""

    as_of_date: date
    near_far: NearFarContracts | None
    oi_by_date: dict[date, int]
    source_observation_refs: tuple[str, ...]


class FuturesSignalInputError(ValueError):
    """Raised when futures observations are insufficient for signal generation."""


def select_near_far_contracts(
    rows: list[FuturesObservationModel],
    *,
    as_of_date: date,
) -> NearFarContracts | None:
    """
    Pick near/far from active KAPAS expiries on as_of_date.

    Near = earliest expiry strictly after as_of_date; far = next expiry.
    """
    day_rows = [
        row
        for row in rows
        if row.as_of_date == as_of_date and row.expiry_date > as_of_date
    ]
    if len(day_rows) < 2:
        return None

    by_expiry = sorted(day_rows, key=lambda row: row.expiry_date)
    return NearFarContracts(
        as_of_date=as_of_date,
        near=by_expiry[0],
        far=by_expiry[1],
    )


def load_observation_series(
    session: Session,
    *,
    commodity_id: str,
    as_of_date: date,
    source: str | None = None,
) -> FuturesObservationSeries:
    """Load futures curve history from as_of_date - ROLLING_WINDOW through as_of_date."""
    start = as_of_date - timedelta(days=ROLLING_WINDOW_DAYS)
    repo = FuturesObservationRepository(session)
    rows = repo.list_by_commodity_date_range(
        commodity_id,
        start,
        as_of_date,
        source=source,
    )
    usable = [r for r in rows if r.validation_status in USABLE_VALIDATION_STATUSES]
    near_far = select_near_far_contracts(usable, as_of_date=as_of_date)

    oi_by_date: dict[date, int] = {}
    refs: list[str] = []
    if near_far is not None:
        near_expiry = near_far.near.expiry_date
        for row in usable:
            if row.expiry_date != near_expiry:
                continue
            refs.append(str(row.observation_id))
            if row.open_interest is not None:
                oi_by_date[row.as_of_date] = row.open_interest

    return FuturesObservationSeries(
        as_of_date=as_of_date,
        near_far=near_far,
        oi_by_date=oi_by_date,
        source_observation_refs=tuple(sorted(set(refs))),
    )


def load_spot_modal_quintal(
    session: Session,
    *,
    commodity_id: str,
    as_of_date: date,
    market_ids: tuple[str, ...],
) -> Decimal | None:
    """Daily median modal across primary markets (₹/quintal) for basis."""
    repo = PriceObservationRepository(session)
    start = as_of_date - timedelta(days=7)
    rows = repo.list_by_commodity_date_range(commodity_id, start, as_of_date)
    allowed = set(market_ids)
    by_market: dict[str, list[Decimal]] = {}
    for row in rows:
        if row.as_of_date != as_of_date:
            continue
        if row.market_id not in allowed:
            continue
        if row.price_type != MODAL_PRICE_TYPE:
            continue
        if row.validation_status not in USABLE_VALIDATION_STATUSES:
            continue
        by_market.setdefault(row.market_id, []).append(row.value)

    if not by_market:
        return None

    market_modals = [
        Decimal(str(median([float(v) for v in values])))
        for values in by_market.values()
    ]
    return Decimal(str(median([float(v) for v in market_modals])))
