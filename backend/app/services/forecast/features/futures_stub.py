"""Futures signal stub for ForecastFeatureSnapshot when Track A is not shipped."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from shared.domain.enums import AgentType, Direction

FUTURES_STUB_REASON = (
    "FuturesSignalGenerator unavailable (no DB session; assembly-only stub)"
)


@dataclass(frozen=True, slots=True)
class FuturesSignalStub:
    """Neutral degraded Futures agent row for feature assembly only."""

    agent_type: str
    direction: str
    magnitude: Decimal
    confidence: Decimal
    value: Decimal
    signal_components: dict[str, object]
    as_of_date: date
    is_stub: bool
    stub_reason: str

    def to_lineage_entry(self) -> dict[str, object]:
        return {
            "source": "stub",
            "agent_type": self.agent_type,
            "stub_reason": self.stub_reason,
            "is_stub": True,
        }


def build_futures_signal_stub(*, as_of_date: date) -> FuturesSignalStub:
    """Deterministic neutral Futures placeholder — no licensed feed required."""
    components: dict[str, object] = {
        "curve_slope": 0.0,
        "curve_level_near": None,
        "open_interest_change": 0.0,
        "basis_futures_spot": 0.0,
        "carry_implied_30": 0.0,
        "carry_implied_60": 0.0,
        "carry_implied_90": 0.0,
        "stub": True,
    }
    return FuturesSignalStub(
        agent_type=AgentType.FUTURES.value,
        direction=Direction.NEUTRAL.value,
        magnitude=Decimal("0"),
        confidence=Decimal("0"),
        value=Decimal("0"),
        signal_components=components,
        as_of_date=as_of_date,
        is_stub=True,
        stub_reason=FUTURES_STUB_REASON,
    )


def structured_signal_lineage_entry(
    *,
    signal_id: UUID | None,
    agent_type: str,
    agent_version: str | None,
    trace_id: UUID | None,
) -> dict[str, object]:
    entry: dict[str, object] = {
        "source": "structured_signal",
        "agent_type": agent_type,
    }
    if signal_id is not None:
        entry["signal_id"] = str(signal_id)
    if agent_version is not None:
        entry["agent_version"] = agent_version
    if trace_id is not None:
        entry["trace_id"] = str(trace_id)
    return entry
