"""Deterministic PI10 forecast dataset fixtures (script + tests; no tests import)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from backend.app.persistence.models.observation import (
    ObservationValidationStatus,
    PriceObservationModel,
)
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.models.signal import SignalSnapshotModel
from backend.app.persistence.validation.signal import (
    build_snapshot_signals,
    compute_snapshot_hash,
    structured_signal_to_persisted_row,
)
from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    DEFAULT_CURRENCY,
    DEFAULT_PRICE_UNIT,
    SOURCE_AGMARKNET,
)
from shared.domain.enums import AgentType, Direction

FIXTURE_REGISTRY_ID = UUID("a1b2c3d4-e5f6-4789-a012-3456789abcde")
FIXTURE_TRACE_ID = UUID("f0e1d2c3-b4a5-4678-9012-abcdef012345")
FIXTURE_WINDOW_END = date(2026, 2, 15)
FIXTURE_WINDOW_DAYS = 150
FIXTURE_WINDOW_START = FIXTURE_WINDOW_END - timedelta(days=FIXTURE_WINDOW_DAYS - 1)

FIXTURE_PRIMARY_MARKETS: tuple[str, ...] = (
    "mkt_tg_khammam_apmc",
    "mkt_tg_warangal",
)


def fixture_registry() -> CommodityRegistryModel:
    return CommodityRegistryModel(
        registry_id=FIXTURE_REGISTRY_ID,
        commodity_id=COTTON_COMMODITY_ID,
        version="1.0.0",
        effective_from=date(2026, 1, 1),
        is_active=True,
        required_agents=["Market", "Futures"],
        decision_rules={
            "msp_proximity_pct": 0.03,
            "default_partial_sell_pct": 0.50,
            "formula_version": "1.0.0",
            "msp_inr_quintal": 7121,
        },
    )


def _price_row(*, obs_date: date, market_id: str, value: Decimal) -> PriceObservationModel:
    return PriceObservationModel(
        observation_id=uuid4(),
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
        validation_status=ObservationValidationStatus.VALIDATED.value,
    )


def fixture_price_window() -> list[PriceObservationModel]:
    """Monotonic rising modal prices — 150 days × 2 primary mandis."""
    rows: list[PriceObservationModel] = []
    for offset in range(FIXTURE_WINDOW_DAYS):
        obs_date = FIXTURE_WINDOW_END - timedelta(days=FIXTURE_WINDOW_DAYS - 1 - offset)
        level = Decimal("6000") + Decimal("15") * offset
        for market_id in FIXTURE_PRIMARY_MARKETS:
            rows.append(_price_row(obs_date=obs_date, market_id=market_id, value=level))
    return rows


def _structured_signal_row(
    agent: AgentType,
    *,
    obs_date: date,
    confidence: Decimal,
) -> dict:
    from backend.app.persistence.models.signal import StructuredSignalModel

    entity = StructuredSignalModel(
        signal_id=uuid4(),
        agent_type=agent.value,
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=obs_date,
        as_of_timestamp=datetime(
            obs_date.year, obs_date.month, obs_date.day, 12, 0, tzinfo=UTC
        ),
        value=Decimal("0.40"),
        direction=Direction.BULLISH.value,
        magnitude=Decimal("0.40"),
        confidence=confidence,
        signal_components={"feature": agent.value.lower()},
        registry_id=FIXTURE_REGISTRY_ID,
    )
    return structured_signal_to_persisted_row(entity)


def _snapshot_for_date(obs_date: date) -> SignalSnapshotModel:
    payloads = [
        _structured_signal_row(
            AgentType.MARKET, obs_date=obs_date, confidence=Decimal("0.70")
        ),
        _structured_signal_row(
            AgentType.WEATHER, obs_date=obs_date, confidence=Decimal("0.65")
        ),
    ]
    signals = build_snapshot_signals(payloads)
    snapshot_hash = compute_snapshot_hash(
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=obs_date,
        registry_id=FIXTURE_REGISTRY_ID,
        signals=payloads,
        trace_id=FIXTURE_TRACE_ID,
    )
    return SignalSnapshotModel(
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=obs_date,
        registry_id=FIXTURE_REGISTRY_ID,
        signal_ids=[],
        signals=signals,
        trace_id=FIXTURE_TRACE_ID,
        snapshot_hash=snapshot_hash,
    )


def fixture_snapshots_by_date() -> dict[date, SignalSnapshotModel]:
    dates = sorted({row.as_of_date for row in fixture_price_window()})
    return {obs_date: _snapshot_for_date(obs_date) for obs_date in dates}


def fixture_primary_markets() -> tuple[str, ...]:
    return FIXTURE_PRIMARY_MARKETS
