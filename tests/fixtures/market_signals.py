"""Fixtures for market signal generator unit tests (E-04-S01)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    ObservationValidationStatus,
    PriceObservationModel,
)
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    DEFAULT_ARRIVAL_UNIT,
    DEFAULT_CURRENCY,
    DEFAULT_PRICE_UNIT,
    SOURCE_AGMARKNET,
)

PRIMARY_MARKETS: tuple[str, ...] = (
    "mkt_tg_khammam_apmc",
    "mkt_tg_warangal",
)

AS_OF_DATE = date(2026, 2, 15)  # inside arrival season (Oct–Mar)


def registry_fixture(*, msp_inr_quintal: float | None = None) -> CommodityRegistryModel:
    rules: dict[str, object] = {
        "msp_proximity_pct": 0.03,
        "default_partial_sell_pct": 0.50,
        "formula_version": "1.0.0",
    }
    if msp_inr_quintal is not None:
        rules["msp_inr_quintal"] = msp_inr_quintal
    return CommodityRegistryModel(
        registry_id=uuid4(),
        commodity_id=COTTON_COMMODITY_ID,
        version="1.0.0",
        effective_from=date(2026, 1, 1),
        is_active=True,
        required_agents=["Market", "Futures"],
        decision_rules=rules,
    )


def _price_row(
    *,
    obs_date: date,
    market_id: str,
    value: Decimal,
    validation_status: str = ObservationValidationStatus.VALIDATED.value,
    observation_id: UUID | None = None,
) -> PriceObservationModel:
    return PriceObservationModel(
        observation_id=observation_id or uuid4(),
        as_of_date=obs_date,
        market_id=market_id,
        commodity_id=COTTON_COMMODITY_ID,
        price_type="modal",
        value=value,
        unit=DEFAULT_PRICE_UNIT,
        currency=DEFAULT_CURRENCY,
        observed_at=datetime(
            obs_date.year, obs_date.month, obs_date.day, 12, 0, tzinfo=UTC
        ),
        source=SOURCE_AGMARKNET,
        validation_status=validation_status,
    )


def _arrival_row(
    *,
    obs_date: date,
    market_id: str,
    volume: Decimal,
    validation_status: str = ObservationValidationStatus.VALIDATED.value,
) -> ArrivalObservationModel:
    return ArrivalObservationModel(
        observation_id=uuid4(),
        as_of_date=obs_date,
        market_id=market_id,
        commodity_id=COTTON_COMMODITY_ID,
        volume=volume,
        unit=DEFAULT_ARRIVAL_UNIT,
        observed_at=datetime(
            obs_date.year, obs_date.month, obs_date.day, 12, 0, tzinfo=UTC
        ),
        source=SOURCE_AGMARKNET,
        validation_status=validation_status,
    )


def rising_price_window(
    *,
    end: date = AS_OF_DATE,
    days: int = 30,
    start_price: Decimal = Decimal("6800"),
    step: Decimal = Decimal("20"),
) -> list[PriceObservationModel]:
    """Monotonic rising modal prices across primary markets."""
    rows: list[PriceObservationModel] = []
    for offset in range(days):
        obs_date = end - timedelta(days=days - 1 - offset)
        level = start_price + step * offset
        for market_id in PRIMARY_MARKETS:
            rows.append(
                _price_row(obs_date=obs_date, market_id=market_id, value=level)
            )
    return rows


def flat_arrival_window(
    *,
    end: date = AS_OF_DATE,
    days: int = 30,
    volume: Decimal = Decimal("100"),
) -> list[ArrivalObservationModel]:
    rows: list[ArrivalObservationModel] = []
    for offset in range(days):
        obs_date = end - timedelta(days=days - 1 - offset)
        for market_id in PRIMARY_MARKETS:
            rows.append(
                _arrival_row(obs_date=obs_date, market_id=market_id, volume=volume)
            )
    return rows


def mixed_validation_prices(
    *,
    end: date = AS_OF_DATE,
    days: int = 5,
) -> list[PriceObservationModel]:
    """Include rejected rows that must be excluded from signal math."""
    rows = rising_price_window(end=end, days=days, start_price=Decimal("7000"))
    rejected = _price_row(
        obs_date=end,
        market_id=PRIMARY_MARKETS[0],
        value=Decimal("9999"),
        validation_status=ObservationValidationStatus.REJECTED.value,
    )
    return rows + [rejected]
