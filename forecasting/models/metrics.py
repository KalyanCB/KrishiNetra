"""Regression metrics for forecast baseline evaluation (TY-01 price level)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True, slots=True)
class RegressionMetrics:
    mae: float
    rmse: float
    mape_pct: float
    n_samples: int

    def to_dict(self) -> dict[str, float | int]:
        return {
            "mae": round(self.mae, 6),
            "rmse": round(self.rmse, 6),
            "mape_pct": round(self.mape_pct, 6),
            "n_samples": self.n_samples,
        }


def regression_metrics(
    y_true: NDArray[np.float64],
    y_pred: NDArray[np.float64],
    *,
    mape_epsilon: float = 1e-6,
) -> RegressionMetrics:
    """MAE, RMSE, and MAPE (percent) on aligned vectors."""
    if y_true.shape != y_pred.shape:
        msg = "y_true and y_pred must have the same shape"
        raise ValueError(msg)
    n = int(y_true.shape[0])
    if n == 0:
        msg = "cannot compute metrics on empty arrays"
        raise ValueError(msg)
    err = y_pred - y_true
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err**2)))
    denom = np.maximum(np.abs(y_true), mape_epsilon)
    mape_pct = float(np.mean(np.abs(err) / denom) * 100.0)
    return RegressionMetrics(mae=mae, rmse=rmse, mape_pct=mape_pct, n_samples=n)
