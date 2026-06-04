"""ForecastModelRegistry value types — PI11 Track E."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class TrainingWindow:
    """Inclusive training date range for a registered model."""

    start: date
    end: date


@dataclass(frozen=True, slots=True)
class ForecastModelMetrics:
    """Backtest / validation metrics persisted on registry entries."""

    mae: float
    rmse: float
    mape: float
    horizon_days: int = 30

    def as_dict(self) -> dict[str, float | int]:
        return {
            "mae": self.mae,
            "rmse": self.rmse,
            "mape": self.mape,
            "horizon_days": self.horizon_days,
        }
