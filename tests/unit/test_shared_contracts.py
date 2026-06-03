"""E-00-S08: Shared domain enums and signal contract tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from shared.domain.enums import (
    ActionType,
    AgentType,
    CommodityType,
    Direction,
    EventType,
    LiquidityNeed,
    MarketRegime,
    PersonaType,
)
from shared.signal_contract.models import StructuredSignal

EXPECTED_AGENT_TYPES = {
    "MARKET",
    "WEATHER",
    "POLICY",
    "DEMAND",
    "FUTURES",
    "GLOBAL",
}

EXPECTED_EVENT_TYPES = {
    "PRICE_UPDATED",
    "ARRIVAL_UPDATED",
    "WEATHER_UPDATED",
    "POLICY_UPDATED",
    "DEMAND_SIGNAL_UPDATED",
    "FUTURES_SIGNAL_UPDATED",
    "GLOBAL_SIGNAL_UPDATED",
    "FORECAST_GENERATED",
    "MI_SNAPSHOT_READY",
    "DECISION_REQUESTED",
    "RECOMMENDATION_GENERATED",
    "EXPLANATION_GENERATED",
    "OUTCOME_CAPTURED",
    "DATA_REFRESH_STARTED",
    "DATA_REFRESH_COMPLETED",
}


def test_enum_values_match_tds() -> None:
    assert {m.name for m in AgentType} == EXPECTED_AGENT_TYPES
    assert AgentType.GLOBAL.value == "Global"
    assert {m.name for m in EventType} == EXPECTED_EVENT_TYPES
    assert ActionType.SELL.value == "SELL"
    assert PersonaType.FARMER.value == "farmer"
    assert LiquidityNeed.HIGH.value == "high"
    assert MarketRegime.NORMAL.value == "NORMAL"
    assert CommodityType.COTTON.value == "cotton"
    assert Direction.BULLISH.value == "bullish"


def test_structured_signal_validation() -> None:
    signal = StructuredSignal(
        agent_type=AgentType.MARKET,
        value=Decimal("0.5"),
        direction=Direction.BULLISH,
        magnitude=Decimal("0.8"),
        confidence=Decimal("0.9"),
        as_of_timestamp=datetime(2026, 6, 3, tzinfo=UTC),
    )
    assert signal.commodity_id == CommodityType.COTTON

    with pytest.raises(ValidationError):
        StructuredSignal(
            agent_type=AgentType.MARKET,
            value=Decimal("0.5"),
            direction=Direction.NEUTRAL,
            magnitude=Decimal("0.5"),
            confidence=Decimal("1.5"),
            as_of_timestamp=datetime(2026, 6, 3, tzinfo=UTC),
        )
