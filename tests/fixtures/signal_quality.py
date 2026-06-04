"""Fixtures for SignalQualityService unit tests (PI9 Track E)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.models.signal import (
    SignalSnapshotModel,
    StructuredSignalModel,
)
from backend.app.persistence.validation.signal import (
    build_snapshot_signals,
    compute_snapshot_hash,
    structured_signal_to_persisted_row,
)
from shared.domain.enums import AgentType, Direction

COTTON_COMMODITY_ID = "cotton"
AS_OF_DATE = date(2026, 6, 4)
AS_OF_TIMESTAMP = datetime(2026, 6, 4, 12, 0, tzinfo=UTC)
NOW_FRESH = datetime(2026, 6, 4, 14, 0, tzinfo=UTC)
NOW_STALE = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


def pi9_registry(*, registry_id: UUID | None = None) -> CommodityRegistryModel:
    """Cotton registry with Market+Futures required and Weather optional."""
    return CommodityRegistryModel(
        registry_id=registry_id or uuid4(),
        commodity_id=COTTON_COMMODITY_ID,
        version="1.0.0",
        effective_from=date(2026, 1, 1),
        is_active=True,
        required_agents=[AgentType.MARKET.value, AgentType.FUTURES.value],
        optional_agents=[
            AgentType.WEATHER.value,
            AgentType.POLICY.value,
        ],
        decision_rules={
            "msp_proximity_pct": 0.03,
            "default_partial_sell_pct": 0.50,
            "formula_version": "1.0.0",
        },
    )


def structured_signal_row(
    agent: AgentType,
    *,
    registry_id: UUID,
    confidence: Decimal = Decimal("0.72"),
    as_of_timestamp: datetime = AS_OF_TIMESTAMP,
    signal_id: UUID | None = None,
) -> StructuredSignalModel:
    return StructuredSignalModel(
        signal_id=signal_id or uuid4(),
        agent_type=agent.value,
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=AS_OF_DATE,
        as_of_timestamp=as_of_timestamp,
        value=Decimal("0.40"),
        direction=Direction.BULLISH.value,
        magnitude=Decimal("0.40"),
        confidence=confidence,
        signal_components={"feature": agent.value.lower()},
        registry_id=registry_id,
    )


def market_and_weather_signals(
    registry_id: UUID,
) -> tuple[StructuredSignalModel, StructuredSignalModel]:
    market = structured_signal_row(
        AgentType.MARKET,
        registry_id=registry_id,
        confidence=Decimal("0.68"),
    )
    weather = structured_signal_row(
        AgentType.WEATHER,
        registry_id=registry_id,
        confidence=Decimal("0.55"),
    )
    return market, weather


def snapshot_for_signals(
    signals: list[StructuredSignalModel],
    *,
    registry_id: UUID,
) -> SignalSnapshotModel:
    signal_ids = [str(row.signal_id) for row in signals]
    trace_id = uuid4()
    persisted = build_snapshot_signals(
        [structured_signal_to_persisted_row(row) for row in signals]
    )
    snapshot_hash = compute_snapshot_hash(
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=AS_OF_DATE,
        registry_id=registry_id,
        signals=persisted,
        trace_id=trace_id,
    )
    return SignalSnapshotModel(
        snapshot_id=uuid4(),
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=AS_OF_DATE,
        registry_id=registry_id,
        signal_ids=signal_ids,
        signals=persisted,
        trace_id=trace_id,
        snapshot_hash=snapshot_hash,
    )
