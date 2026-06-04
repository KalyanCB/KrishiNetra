"""Random Forest baseline for PI11 Track C — delegates to Track A ``baselines`` module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.ensemble import RandomForestRegressor

from forecasting.models.baselines import (
    build_random_forest,
)

DEFAULT_MODELS_DIR = Path("data/forecast_models")
TRACK_A_RF_NAME = "random_forest"


def fit_random_forest_baseline(
    features: NDArray[np.float64],
    targets: NDArray[np.float64],
) -> RandomForestRegressor:
    """Fit Track A Random Forest config on the supplied panel."""
    model = build_random_forest()
    model.fit(features, targets)
    return model


def feature_importance_map(
    model: RandomForestRegressor,
    feature_names: tuple[str, ...],
) -> dict[str, float]:
    """Map ``feature_importances_`` to feature names (stable sorted keys)."""
    raw = model.feature_importances_
    return {
        name: round(float(score), 10)
        for name, score in zip(feature_names, raw, strict=True)
    }


def track_a_artifact_path(
    horizon_days: int,
    *,
    models_dir: Path | None = None,
) -> Path:
    root = models_dir or DEFAULT_MODELS_DIR
    return root / f"{horizon_days}d" / f"{TRACK_A_RF_NAME}.joblib"


def load_track_a_random_forest(
    horizon_days: int,
    *,
    models_dir: Path | None = None,
) -> tuple[RandomForestRegressor, tuple[str, ...]] | None:
    """Load Track A ``random_forest`` joblib bundle when present on disk."""
    path = track_a_artifact_path(horizon_days, models_dir=models_dir)
    if not path.is_file():
        return None
    try:
        import joblib
    except ImportError:
        return None
    payload: Any = joblib.load(path)
    if not isinstance(payload, dict):
        return None
    model = payload.get("model")
    names = payload.get("feature_names")
    if not isinstance(model, RandomForestRegressor):
        return None
    if not isinstance(names, (list, tuple)):
        return None
    return model, tuple(str(n) for n in names)
