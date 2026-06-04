"""Pure signal quality metric helpers (PI9 Track E)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from statistics import mean
from uuid import UUID

from backend.app.services.quality.metrics import (
    STALE_LAG_HOURS,
    classify_source_health,
    coverage_ratio,
    lag_hours,
)

DEFAULT_SIGNAL_STALE_LAG_HOURS = STALE_LAG_HOURS


@dataclass(frozen=True, slots=True)
class SignalConfidenceAggregates:
    """Confidence rollups across agent rows for a commodity/day."""

    count: int
    min_confidence: Decimal | None
    max_confidence: Decimal | None
    mean_confidence: Decimal | None
    by_agent: dict[str, Decimal]

    def to_detail(self) -> dict[str, float | int | dict[str, str] | None]:
        return {
            "count": self.count,
            "min": float(self.min_confidence) if self.min_confidence is not None else None,
            "max": float(self.max_confidence) if self.max_confidence is not None else None,
            "mean": float(self.mean_confidence) if self.mean_confidence is not None else None,
            "by_agent": {
                agent: format(confidence, "f")
                for agent, confidence in sorted(self.by_agent.items())
            },
        }


@dataclass(frozen=True, slots=True)
class SignalQualityMetrics:
    """Computed signal coverage, freshness, and confidence for one MI day."""

    commodity_id: str
    as_of_date: date
    registry_id: UUID
    signal_count: int
    snapshot_signal_count: int
    snapshot_present: bool
    snapshot_hash: str | None
    snapshot_aligned: bool
    agents_expected: int
    agents_present: int
    required_agents_expected: int
    required_agents_present: int
    coverage_ratio: float
    required_coverage_ratio: float
    signals_missing: tuple[str, ...]
    optional_agents_missing: tuple[str, ...]
    agents_present_list: tuple[str, ...]
    latest_as_of_timestamp: datetime | None
    signal_lag_hours: float | None
    freshness: str
    confidence: SignalConfidenceAggregates

    def to_report_detail(self) -> dict[str, object]:
        return {
            "signal_count": self.signal_count,
            "snapshot_signal_count": self.snapshot_signal_count,
            "snapshot_present": self.snapshot_present,
            "snapshot_aligned": self.snapshot_aligned,
            "coverage_ratio": round(self.coverage_ratio, 4),
            "required_coverage_ratio": round(self.required_coverage_ratio, 4),
            "signals_missing": list(self.signals_missing),
            "optional_agents_missing": list(self.optional_agents_missing),
            "agents_present": list(self.agents_present_list),
            "signal_lag_hours": (
                round(self.signal_lag_hours, 2)
                if self.signal_lag_hours is not None
                else None
            ),
            "freshness": self.freshness,
            "confidence": self.confidence.to_detail(),
        }


def compute_confidence_aggregates(
    *,
    agent_confidences: dict[str, Decimal],
) -> SignalConfidenceAggregates:
    """Aggregate per-agent confidence values."""
    if not agent_confidences:
        return SignalConfidenceAggregates(
            count=0,
            min_confidence=None,
            max_confidence=None,
            mean_confidence=None,
            by_agent={},
        )
    values = list(agent_confidences.values())
    mean_value = Decimal(str(round(mean(float(v) for v in values), 4)))
    return SignalConfidenceAggregates(
        count=len(values),
        min_confidence=min(values),
        max_confidence=max(values),
        mean_confidence=mean_value,
        by_agent=dict(agent_confidences),
    )


def classify_signal_freshness(
    *,
    signal_lag_hours: float | None,
    has_signals: bool,
    stale_lag_hours: float = DEFAULT_SIGNAL_STALE_LAG_HOURS,
) -> str:
    """Map signal lag to TDS fresh / stale / missing."""
    if not has_signals:
        return "missing"
    return classify_source_health(
        coverage_ratio=1.0 if has_signals else 0.0,
        completeness_ratio=1.0 if has_signals else 0.0,
        lag_hours_value=signal_lag_hours,
        has_data=has_signals,
        stale_lag_hours=stale_lag_hours,
    )


def build_signal_quality_metrics(
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    agent_confidences: dict[str, Decimal],
    required_agents: list[str],
    optional_agents: list[str] | None,
    latest_as_of_timestamp: datetime | None,
    snapshot_signal_count: int,
    snapshot_present: bool,
    snapshot_hash: str | None,
    now: datetime,
) -> SignalQualityMetrics:
    """Pure assembly of signal quality metrics from loaded rows."""
    present = tuple(sorted(agent_confidences.keys()))
    required = tuple(required_agents)
    optional = tuple(optional_agents or [])
    expected = required + optional

    signals_missing = tuple(agent for agent in required if agent not in present)
    optional_missing = tuple(agent for agent in optional if agent not in present)

    signal_count = len(present)
    required_present = sum(1 for agent in required if agent in present)
    lag = lag_hours(latest_as_of_timestamp, now=now)
    freshness = classify_signal_freshness(
        signal_lag_hours=lag,
        has_signals=signal_count > 0,
    )
    confidence = compute_confidence_aggregates(agent_confidences=agent_confidences)

    return SignalQualityMetrics(
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry_id=registry_id,
        signal_count=signal_count,
        snapshot_signal_count=snapshot_signal_count,
        snapshot_present=snapshot_present,
        snapshot_hash=snapshot_hash,
        snapshot_aligned=(
            snapshot_present and signal_count == snapshot_signal_count
        ),
        agents_expected=len(expected),
        agents_present=signal_count,
        required_agents_expected=len(required),
        required_agents_present=required_present,
        coverage_ratio=coverage_ratio(signal_count, len(expected)),
        required_coverage_ratio=coverage_ratio(required_present, len(required)),
        signals_missing=signals_missing,
        optional_agents_missing=optional_missing,
        agents_present_list=present,
        latest_as_of_timestamp=latest_as_of_timestamp,
        signal_lag_hours=lag,
        freshness=freshness,
        confidence=confidence,
    )
