"""PI11 Track D forecast quality evaluation fixtures."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from backend.app.services.forecast.quality.metrics import ForecastEvaluationPair

COTTON_COMMODITY_ID = "cotton"
AS_OF_DATE = date(2025, 12, 1)
REGISTRY_ID = UUID("a1b2c3d4-e5f6-4789-a012-3456789abcde")
MODEL_VERSION = "v0.1.0-pi11"


def sample_evaluation_pairs() -> list[ForecastEvaluationPair]:
    """Deterministic pairs for unit tests (30d horizon)."""
    return [
        ForecastEvaluationPair(
            predicted=100.0,
            actual=110.0,
            horizon_days=30,
            band_low=95.0,
            band_high=115.0,
        ),
        ForecastEvaluationPair(
            predicted=200.0,
            actual=180.0,
            horizon_days=30,
            band_low=170.0,
            band_high=210.0,
        ),
        ForecastEvaluationPair(
            predicted=50.0,
            actual=52.0,
            horizon_days=30,
            band_low=40.0,
            band_high=49.0,
        ),
    ]


def multi_horizon_evaluation_pairs() -> list[ForecastEvaluationPair]:
    """Pairs across 30/60/90-day horizons."""
    return [
        ForecastEvaluationPair(
            predicted=6000.0,
            actual=6100.0,
            horizon_days=30,
            band_low=5900.0,
            band_high=6200.0,
        ),
        ForecastEvaluationPair(
            predicted=6100.0,
            actual=6300.0,
            horizon_days=60,
            band_low=6000.0,
            band_high=6400.0,
        ),
        ForecastEvaluationPair(
            predicted=6200.0,
            actual=6500.0,
            horizon_days=90,
            band_low=6100.0,
            band_high=6600.0,
        ),
    ]
