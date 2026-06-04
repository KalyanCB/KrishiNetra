"""Pure forecast quality metric helpers (PI11 Track D)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import mean

DEFAULT_HORIZONS = (30, 60, 90)
MIN_ACTUAL_FOR_MAPE = 1e-6


@dataclass(frozen=True, slots=True)
class ForecastEvaluationPair:
    """One forecast vs realized price observation for backtest evaluation."""

    predicted: float
    actual: float
    horizon_days: int
    band_low: float | None = None
    band_high: float | None = None
    as_of_date: str | None = None


@dataclass(frozen=True, slots=True)
class HorizonQualityMetrics:
    """MAE, RMSE, MAPE, and interval coverage for one horizon."""

    horizon_days: int
    sample_count: int
    mae: float | None
    rmse: float | None
    mape: float | None
    coverage: float | None

    def to_detail(self) -> dict[str, float | int | None]:
        return {
            "horizon_days": self.horizon_days,
            "sample_count": self.sample_count,
            "mae": round(self.mae, 4) if self.mae is not None else None,
            "rmse": round(self.rmse, 4) if self.rmse is not None else None,
            "mape": round(self.mape, 4) if self.mape is not None else None,
            "coverage": round(self.coverage, 4) if self.coverage is not None else None,
        }


def compute_mae(*, errors: list[float]) -> float | None:
    """Mean absolute error over signed residuals (predicted - actual)."""
    if not errors:
        return None
    return mean(abs(value) for value in errors)


def compute_rmse(*, errors: list[float]) -> float | None:
    """Root mean square error."""
    if not errors:
        return None
    return math.sqrt(mean(value * value for value in errors))


def compute_mape(
    *,
    predicted: list[float],
    actual: list[float],
    min_actual: float = MIN_ACTUAL_FOR_MAPE,
) -> float | None:
    """
    Mean absolute percentage error in percent (TDS-000 §2.2).

    Rows with |actual| below ``min_actual`` are excluded.
    """
    pct_errors: list[float] = []
    for pred, act in zip(predicted, actual, strict=True):
        if abs(act) < min_actual:
            continue
        pct_errors.append(abs((pred - act) / act) * 100.0)
    if not pct_errors:
        return None
    return mean(pct_errors)


def compute_interval_coverage(
    *,
    actual: list[float],
    band_low: list[float | None],
    band_high: list[float | None],
) -> float | None:
    """
    Fraction of realizations inside [band_low, band_high] (TDS-011 §5.1).

    Only rows with both bounds contribute to the denominator.
    """
    hits = 0
    total = 0
    for realized, low, high in zip(actual, band_low, band_high, strict=True):
        if low is None or high is None:
            continue
        total += 1
        if low <= realized <= high:
            hits += 1
    if total == 0:
        return None
    return hits / total


def build_horizon_quality_metrics(
    pairs: list[ForecastEvaluationPair],
    *,
    horizon_days: int,
) -> HorizonQualityMetrics:
    """Aggregate KPIs for one horizon from evaluation pairs."""
    subset = [row for row in pairs if row.horizon_days == horizon_days]
    if not subset:
        return HorizonQualityMetrics(
            horizon_days=horizon_days,
            sample_count=0,
            mae=None,
            rmse=None,
            mape=None,
            coverage=None,
        )

    errors = [row.predicted - row.actual for row in subset]
    predicted = [row.predicted for row in subset]
    actual = [row.actual for row in subset]
    lows = [row.band_low for row in subset]
    highs = [row.band_high for row in subset]

    return HorizonQualityMetrics(
        horizon_days=horizon_days,
        sample_count=len(subset),
        mae=compute_mae(errors=errors),
        rmse=compute_rmse(errors=errors),
        mape=compute_mape(predicted=predicted, actual=actual),
        coverage=compute_interval_coverage(
            actual=actual,
            band_low=lows,
            band_high=highs,
        ),
    )


def build_forecast_quality_by_horizon(
    pairs: list[ForecastEvaluationPair],
    *,
    horizons: tuple[int, ...] = DEFAULT_HORIZONS,
) -> dict[int, HorizonQualityMetrics]:
    """Compute MAE, RMSE, MAPE, and coverage per horizon."""
    return {
        horizon: build_horizon_quality_metrics(pairs, horizon_days=horizon)
        for horizon in horizons
    }


def pair_from_horizon_payload(
    *,
    horizon_days: int,
    horizon: dict[str, object],
    actual_price: float,
    as_of_date: str | None = None,
) -> ForecastEvaluationPair:
    """Build an evaluation pair from ForecastVersion horizon JSON."""
    point = horizon["point"]
    band_low = horizon.get("band_low")
    band_high = horizon.get("band_high")
    return ForecastEvaluationPair(
        predicted=float(point),  # type: ignore[arg-type]
        actual=actual_price,
        horizon_days=horizon_days,
        band_low=float(band_low) if band_low is not None else None,  # type: ignore[arg-type]
        band_high=float(band_high) if band_high is not None else None,  # type: ignore[arg-type]
        as_of_date=as_of_date,
    )
