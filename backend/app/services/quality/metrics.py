"""Pure quality metric helpers for data_quality_snapshot (TDS-006 §3.17)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal

from backend.app.persistence.models.observation import ObservationValidationStatus

DEFAULT_WINDOW_DAYS = 30
STALE_LAG_HOURS = 48.0
VALID_VALIDATION_STATUSES = frozenset(
    {
        ObservationValidationStatus.VALIDATED.value,
        ObservationValidationStatus.PUBLISHED.value,
    }
)


@dataclass(frozen=True, slots=True)
class AgmarknetQualityMetrics:
    """Computed Agmarknet coverage, freshness, completeness, and anomalies."""

    markets_expected: int
    markets_reporting: int
    coverage_ratio: float
    window_days: int
    days_with_data: int
    completeness_ratio: float
    latest_as_of_date: date | None
    latest_observed_at: datetime | None
    agmarknet_lag_hours: float | None
    anomaly_count: int

    def to_source_health_detail(self) -> dict[str, int | float | str | None]:
        return {
            "markets_expected": self.markets_expected,
            "markets_reporting": self.markets_reporting,
            "coverage_ratio": round(self.coverage_ratio, 4),
            "window_days": self.window_days,
            "days_with_data": self.days_with_data,
            "completeness_ratio": round(self.completeness_ratio, 4),
            "latest_as_of_date": (
                self.latest_as_of_date.isoformat() if self.latest_as_of_date else None
            ),
            "anomaly_count": self.anomaly_count,
        }


@dataclass(frozen=True, slots=True)
class WeatherQualityMetrics:
    """Computed NASA POWER / weather belt coverage in the quality window."""

    regions_expected: int
    regions_reporting: int
    coverage_ratio: float
    window_days: int
    days_with_data: int
    completeness_ratio: float
    latest_as_of_date: date | None
    latest_observed_at: datetime | None
    weather_lag_hours: float | None
    anomaly_count: int

    def to_source_health_detail(self) -> dict[str, int | float | str | None]:
        return {
            "regions_expected": self.regions_expected,
            "regions_reporting": self.regions_reporting,
            "coverage_ratio": round(self.coverage_ratio, 4),
            "window_days": self.window_days,
            "days_with_data": self.days_with_data,
            "completeness_ratio": round(self.completeness_ratio, 4),
            "latest_as_of_date": (
                self.latest_as_of_date.isoformat() if self.latest_as_of_date else None
            ),
            "anomaly_count": self.anomaly_count,
        }


def coverage_ratio(reporting: int, expected: int) -> float:
    if expected <= 0:
        return 0.0
    return min(1.0, reporting / expected)


def completeness_ratio(days_with_data: int, window_days: int) -> float:
    if window_days <= 0:
        return 0.0
    return min(1.0, days_with_data / window_days)


def lag_hours(latest_observed_at: datetime | None, *, now: datetime) -> float | None:
    if latest_observed_at is None:
        return None
    delta = now - latest_observed_at
    return max(0.0, delta.total_seconds() / 3600.0)


def classify_source_health(
    *,
    coverage_ratio: float,
    completeness_ratio: float,
    lag_hours_value: float | None,
    has_data: bool,
    stale_lag_hours: float = STALE_LAG_HOURS,
) -> str:
    """Map metrics to TDS fresh / stale / missing."""
    if not has_data or coverage_ratio <= 0.0:
        return "missing"
    if lag_hours_value is not None and lag_hours_value > stale_lag_hours:
        return "stale"
    if coverage_ratio < 0.5 or completeness_ratio < 0.25:
        return "stale"
    return "fresh"


def compute_overall_quality_score(
    *,
    coverage_ratio: float,
    completeness_ratio: float,
    lag_hours_value: float | None,
    anomaly_count: int,
    row_count: int,
) -> Decimal:
    """Blend coverage, completeness, freshness, and anomaly penalty into [0, 1]."""
    freshness = 1.0
    if lag_hours_value is not None:
        freshness = max(0.0, 1.0 - (lag_hours_value / 168.0))
    anomaly_penalty = 0.0
    if row_count > 0 and anomaly_count > 0:
        anomaly_penalty = min(0.3, anomaly_count / row_count)
    raw = (
        0.4 * coverage_ratio
        + 0.35 * completeness_ratio
        + 0.25 * freshness
        - anomaly_penalty
    )
    return Decimal(str(round(max(0.0, min(1.0, raw)), 4)))


def confidence_penalty_from_score(overall_quality_score: Decimal) -> Decimal:
    """Penalty factor increases as overall quality drops."""
    penalty = 1.0 - float(overall_quality_score)
    return Decimal(str(round(max(0.0, min(1.0, penalty)), 4)))


def default_quality_window(
    as_of_date: date,
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
) -> tuple[date, date]:
    """Inclusive calendar window ending at as_of_date."""
    start = as_of_date - timedelta(days=window_days - 1)
    return start, as_of_date
