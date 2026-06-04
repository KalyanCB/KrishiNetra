"""Basket spot level from validated modal prices (TDS-007 §5.2 spot_price_level)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from statistics import median

from backend.app.persistence.models.observation import PriceObservationModel
from backend.app.services.quality.metrics import VALID_VALIDATION_STATUSES

MODAL_PRICE_TYPE = "modal"


def filter_validated_primary_prices(
    rows: list[PriceObservationModel],
    market_ids: tuple[str, ...],
) -> list[PriceObservationModel]:
    allowed = set(market_ids)
    return [
        row
        for row in rows
        if row.market_id in allowed
        and row.validation_status in VALID_VALIDATION_STATUSES
        and row.price_type == MODAL_PRICE_TYPE
    ]


def basket_modals_by_date(
    prices: list[PriceObservationModel],
) -> dict[date, Decimal]:
    """Daily median of per-market modal medians (MarketSignalGenerator parity)."""
    by_date_market: dict[tuple[date, str], list[Decimal]] = {}
    for row in prices:
        key = (row.as_of_date, row.market_id)
        by_date_market.setdefault(key, []).append(row.value)

    by_date: dict[date, list[Decimal]] = {}
    for (obs_date, _market), values in by_date_market.items():
        market_modal = Decimal(str(median([float(v) for v in values])))
        by_date.setdefault(obs_date, []).append(market_modal)

    return {
        obs_date: Decimal(str(median([float(v) for v in market_modals])))
        for obs_date, market_modals in by_date.items()
    }
