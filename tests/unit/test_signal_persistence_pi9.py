"""PI9 Track C: SignalSnapshot PI9 contract persistence tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from backend.app.persistence.models.signal import StructuredSignalModel
from backend.app.persistence.repositories.signal import SignalSnapshotRepository
from backend.app.persistence.validation.signal import (
    PI9_AS_OF_DATE,
    PI9_SIGNAL_CONFIDENCE,
    PI9_SIGNAL_DIRECTION,
    PI9_SIGNAL_INPUTS,
    PI9_SIGNAL_MAGNITUDE,
    PI9_SIGNAL_TYPE,
    SignalValidationError,
    build_snapshot_signals,
    compute_snapshot_hash,
    normalize_signal_payload,
    structured_signal_to_persisted_row,
    validate_trace_id,
)
from shared.domain.enums import AgentType, Direction
from shared.persistence.contracts import ImmutableVersionUpdateError


def _payload(
    agent: AgentType,
    *,
    as_of_date: date = date(2026, 6, 4),
) -> dict[str, object]:
    return {
        "agent_type": agent.value,
        "value": Decimal("0.55"),
        "direction": Direction.BULLISH.value,
        "magnitude": Decimal("0.40"),
        "confidence": Decimal("0.75"),
        "signal_components": {"feature": "z"},
        "as_of_date": as_of_date,
    }


def test_normalize_accepts_tds006_keys() -> None:
    row = normalize_signal_payload(_payload(AgentType.MARKET))
    assert row[PI9_SIGNAL_TYPE] == AgentType.MARKET.value
    assert row[PI9_SIGNAL_DIRECTION] == Direction.BULLISH.value
    assert row[PI9_SIGNAL_MAGNITUDE] == "0.40"
    assert row[PI9_SIGNAL_CONFIDENCE] == "0.75"
    assert row[PI9_SIGNAL_INPUTS] == {"feature": "z"}
    assert row[PI9_AS_OF_DATE] == "2026-06-04"


def test_normalize_accepts_pi9_keys() -> None:
    row = normalize_signal_payload(
        {
            PI9_SIGNAL_TYPE: AgentType.WEATHER.value,
            PI9_SIGNAL_DIRECTION: Direction.NEUTRAL.value,
            PI9_SIGNAL_MAGNITUDE: Decimal("0.20"),
            PI9_SIGNAL_CONFIDENCE: Decimal("0.60"),
            PI9_SIGNAL_INPUTS: {"rainfall_anomaly_7d": -0.1},
            PI9_AS_OF_DATE: date(2026, 6, 4),
        }
    )
    assert row[PI9_SIGNAL_TYPE] == AgentType.WEATHER.value


def test_build_snapshot_signals_sorted_by_type() -> None:
    rows = build_snapshot_signals(
        [_payload(AgentType.FUTURES), _payload(AgentType.MARKET)]
    )
    assert rows[0][PI9_SIGNAL_TYPE] == AgentType.FUTURES.value
    assert rows[1][PI9_SIGNAL_TYPE] == AgentType.MARKET.value


def test_structured_signal_to_persisted_row() -> None:
    entity = StructuredSignalModel(
        signal_id=uuid4(),
        agent_type=AgentType.POLICY.value,
        commodity_id="cotton",
        as_of_date=date(2026, 6, 4),
        as_of_timestamp=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        value=Decimal("0.30"),
        direction=Direction.BEARISH.value,
        magnitude=Decimal("0.50"),
        confidence=Decimal("0.80"),
        signal_components={"msp_inr_quintal": 7121},
        registry_id=uuid4(),
    )
    row = structured_signal_to_persisted_row(entity)
    assert row[PI9_SIGNAL_TYPE] == AgentType.POLICY.value
    assert row[PI9_SIGNAL_INPUTS] == {"msp_inr_quintal": 7121}


def test_snapshot_hash_includes_trace_id() -> None:
    registry_id = uuid4()
    trace_id = uuid4()
    signals = [_payload(AgentType.MARKET)]
    without = compute_snapshot_hash(
        commodity_id="cotton",
        as_of_date=date(2026, 6, 4),
        registry_id=registry_id,
        signals=signals,
    )
    with_trace = compute_snapshot_hash(
        commodity_id="cotton",
        as_of_date=date(2026, 6, 4),
        registry_id=registry_id,
        signals=signals,
        trace_id=trace_id,
    )
    assert without != with_trace


def test_validate_trace_id_required() -> None:
    with pytest.raises(SignalValidationError, match="trace_id"):
        validate_trace_id(None)


def test_signal_snapshot_repository_blocks_update() -> None:
    repo = SignalSnapshotRepository(MagicMock())
    with pytest.raises(ImmutableVersionUpdateError):
        repo.update(MagicMock())
