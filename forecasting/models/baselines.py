"""PI11 Track A — deterministic sklearn baselines (no LLM / decision path)."""

from __future__ import annotations

from typing import Protocol, cast

import numpy as np
from numpy.typing import NDArray
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from forecasting.datasets.training import SPOT_FEATURE_NAME

BASELINE_MODEL_SEED = 42
RANDOM_FOREST_ESTIMATORS = 50


class PriceLevelModel(Protocol):
    def fit(self, X: NDArray[np.float64], y: NDArray[np.float64]) -> None: ...

    def predict(self, X: NDArray[np.float64]) -> NDArray[np.float64]: ...


class NaivePersistenceBaseline:
    """TY-01 naive: predicted price at T+h equals spot at T (column ``spot_price_level``)."""

    def __init__(self, *, spot_column: int = 0) -> None:
        self._spot_column = spot_column

    def fit(self, X: NDArray[np.float64], y: NDArray[np.float64]) -> None:
        _ = (X, y)

    def predict(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        return X[:, self._spot_column].astype(np.float64, copy=True)


def spot_column_index(feature_names: tuple[str, ...]) -> int:
    try:
        return feature_names.index(SPOT_FEATURE_NAME)
    except ValueError as exc:
        msg = f"{SPOT_FEATURE_NAME} missing from feature_names"
        raise ValueError(msg) from exc


def build_linear_regression() -> LinearRegression:
    return LinearRegression()


def build_random_forest() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=RANDOM_FOREST_ESTIMATORS,
        random_state=BASELINE_MODEL_SEED,
        n_jobs=1,
    )


BASELINE_MODEL_NAMES: tuple[str, ...] = (
    "naive_persistence",
    "linear_regression",
    "random_forest",
)


def build_baseline_model(
    name: str,
    *,
    feature_names: tuple[str, ...],
) -> PriceLevelModel:
    if name == "naive_persistence":
        return NaivePersistenceBaseline(spot_column=spot_column_index(feature_names))
    if name == "linear_regression":
        return cast(PriceLevelModel, build_linear_regression())
    if name == "random_forest":
        return cast(PriceLevelModel, build_random_forest())
    msg = f"unknown baseline model: {name}"
    raise ValueError(msg)
