"""Fixtures for futures signal generator unit tests (E-04 F-04-05)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from backend.app.persistence.models.futures import FuturesObservationModel
from backend.app.persistence.models.observation import (
    ObservationValidationStatus,
    PriceObservationModel,
)
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    DEFAULT_CURRENCY,
    DEFAULT_PRICE_UNIT,
    SOURCE_AGMARKNET,
)
from backend.app.services.ingest.ncdex.constants import (
    DEFAULT_QUOTE_UNIT,
    ENVIRONMENT_PROTOTYPE,
    SOURCE_NCDEX_PUBLIC_BHAV,
)
from backend.app.services.signals.futures.constants import ROLLING_WINDOW_DAYS

PRIMARY_MARKETS: tuple[str, ...] = (
    "mkt_tg_khammam_apmc",
    "mkt_tg_warangal",
)

AS_OF_DATE = date(2026, 2, 15)

NEAR_EXPIRY = date(2026, 2, 28)
FAR_EXPIRY = date(2026, 4, 30)
THIRD_EXPIRY = date(2026, 11, 30)

NEAR_SETTLE = Decimal("1345.50")
FAR_SETTLE = Decimal("1310.25")
SPOT_MODAL = Decimal("6500")


def registry_fixture() -> CommodityRegistryModel:
    return CommodityRegistryModel(
        registry_id=uuid4(),
        commodity_id=COTTON_COMMODITY_ID,
        version="1.0.0",
        effective_from=date(2026, 1, 1),
        is_active=True,
        required_agents=["Market", "Futures"],
        decision_rules={
            "msp_proximity_pct": 0.03,
            "default_partial_sell_pct": 0.50,
            "formula_version": "1.0.0",
        },
    )


def _futures_row(
    *,
    obs_date: date,
    expiry_date: date,
    settle_price: Decimal,
    open_interest: int | None = 40,
    validation_status: str = ObservationValidationStatus.VALIDATED.value,
    observation_id: UUID | None = None,
) -> FuturesObservationModel:
    return FuturesObservationModel(
        observation_id=observation_id or uuid4(),
        as_of_date=obs_date,
        commodity_id=COTTON_COMMODITY_ID,
        contract_symbol="KAPAS",
        expiry_date=expiry_date,
        settle_price=settle_price,
        quote_unit=DEFAULT_QUOTE_UNIT,
        settle_price_quintal=settle_price * Decimal("5"),
        open_interest=open_interest,
        volume=Decimal("8"),
        observed_at=datetime(
            obs_date.year, obs_date.month, obs_date.day, 17, 30, tzinfo=UTC
        ),
        source=SOURCE_NCDEX_PUBLIC_BHAV,
        environment=ENVIRONMENT_PROTOTYPE,
        provenance={"parser": "udiff_v1"},
        validation_status=validation_status,
    )


def kapas_curve_window(
    *,
    end: date = AS_OF_DATE,
    near_settle: Decimal = NEAR_SETTLE,
    far_settle: Decimal = FAR_SETTLE,
) -> list[FuturesObservationModel]:
    """Rolling near/far KAPAS contracts for OI z-score window."""
    rows: list[FuturesObservationModel] = []
    for offset in range(ROLLING_WINDOW_DAYS):
        obs_date = end - timedelta(days=ROLLING_WINDOW_DAYS - 1 - offset)
        oi = 30 + offset
        rows.append(
            _futures_row(
                obs_date=obs_date,
                expiry_date=NEAR_EXPIRY,
                settle_price=near_settle,
                open_interest=oi,
            )
        )
        rows.append(
            _futures_row(
                obs_date=obs_date,
                expiry_date=FAR_EXPIRY,
                settle_price=far_settle,
                open_interest=25 + offset,
            )
        )
        rows.append(
            _futures_row(
                obs_date=obs_date,
                expiry_date=THIRD_EXPIRY,
                settle_price=Decimal("1288.00"),
                open_interest=20,
            )
        )
    return rows


def spot_price_row(
    *,
    obs_date: date = AS_OF_DATE,
    value: Decimal = SPOT_MODAL,
) -> PriceObservationModel:
    return PriceObservationModel(
        observation_id=uuid4(),
        as_of_date=obs_date,
        market_id=PRIMARY_MARKETS[0],
        commodity_id=COTTON_COMMODITY_ID,
        price_type="modal",
        value=value,
        unit=DEFAULT_PRICE_UNIT,
        currency=DEFAULT_CURRENCY,
        observed_at=datetime(
            obs_date.year, obs_date.month, obs_date.day, 12, 0, tzinfo=UTC
        ),
        source=SOURCE_AGMARKNET,
        validation_status=ObservationValidationStatus.VALIDATED.value,
    )
