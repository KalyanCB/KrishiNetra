"""ForecastModelRegistry validation — PI11 Track E."""

from __future__ import annotations

from datetime import date
from typing import Any


class ForecastModelRegistryValidationError(ValueError):
    """Raised when model registry fields fail validation."""


METRIC_KEYS = ("mae", "rmse", "mape")


def validate_training_window(*, start: date, end: date) -> None:
    if start > end:
        raise ForecastModelRegistryValidationError(
            f"training_window_start {start} must be <= training_window_end {end}"
        )


def validate_feature_set_hash(feature_set_hash: str) -> None:
    if len(feature_set_hash) != 64:
        raise ForecastModelRegistryValidationError(
            f"feature_set_hash must be 64 hex chars, got length {len(feature_set_hash)}"
        )
    if not all(c in "0123456789abcdef" for c in feature_set_hash.lower()):
        raise ForecastModelRegistryValidationError(
            "feature_set_hash must be lowercase hex SHA-256"
        )


def validate_horizon_days(horizon_days: int) -> None:
    if horizon_days not in (30, 60, 90):
        raise ForecastModelRegistryValidationError(
            f"horizon_days must be 30, 60, or 90, got {horizon_days}"
        )


def validate_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    missing = [key for key in METRIC_KEYS if key not in metrics]
    if missing:
        raise ForecastModelRegistryValidationError(
            f"metrics missing required keys: {missing}"
        )
    normalized: dict[str, float] = {}
    for key in METRIC_KEYS:
        value = metrics[key]
        if not isinstance(value, (int, float)):
            raise ForecastModelRegistryValidationError(
                f"metrics.{key} must be numeric, got {type(value).__name__}"
            )
        numeric = float(value)
        if numeric < 0.0:
            raise ForecastModelRegistryValidationError(
                f"metrics.{key} must be non-negative, got {numeric}"
            )
        normalized[key] = numeric
    return normalized
