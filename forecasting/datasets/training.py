"""PI11 Track A — supervised training matrices from PI10 forecast datasets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

import numpy as np
from numpy.typing import NDArray
from sqlalchemy.orm import Session

from forecasting.datasets.builder import (
    FORECAST_HORIZONS,
    BuildResult,
    ForecastDatasetBuilder,
    ForecastDatasetRow,
    build_fixture_datasets,
)
from forecasting.datasets.fixtures import (
    FIXTURE_WINDOW_END,
    FIXTURE_WINDOW_START,
    fixture_price_window,
    fixture_primary_markets,
    fixture_snapshots_by_date,
)

SPOT_FEATURE_NAME = "spot_price_level"
FIXTURE_TRAINING_SEED = 42


def _to_float(value: Decimal | float | int) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _numeric_feature_value(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


@dataclass(frozen=True, slots=True)
class ForecastTrainingDataset:
    """Time-ordered feature matrix and price-level targets for one horizon."""

    horizon_days: int
    commodity_id: str
    as_of_dates: tuple[date, ...]
    feature_names: tuple[str, ...]
    X: NDArray[np.float64]
    y: NDArray[np.float64]
    mode: str

    @property
    def n_samples(self) -> int:
        return int(self.y.shape[0])

    @property
    def n_features(self) -> int:
        return int(self.X.shape[1])

    def spot_levels(self) -> NDArray[np.float64]:
        idx = self.feature_names.index(SPOT_FEATURE_NAME)
        return self.X[:, idx].copy()


def _rows_for_horizon(
    result: BuildResult,
    horizon_days: int,
) -> tuple[ForecastDatasetRow, ...]:
    if horizon_days not in result.datasets:
        msg = f"horizon {horizon_days} not in build result"
        raise ValueError(msg)
    return result.datasets[horizon_days]


def _feature_names_from_rows(rows: tuple[ForecastDatasetRow, ...]) -> tuple[str, ...]:
    keys: set[str] = set()
    for row in rows:
        for key, value in row.features.items():
            if _numeric_feature_value(value) is not None:
                keys.add(key)
    return (SPOT_FEATURE_NAME, *sorted(keys))


def _matrix_from_rows(
    rows: tuple[ForecastDatasetRow, ...],
    feature_names: tuple[str, ...],
) -> tuple[tuple[date, ...], NDArray[np.float64], NDArray[np.float64]]:
    n = len(rows)
    n_features = len(feature_names)
    X = np.zeros((n, n_features), dtype=np.float64)
    y = np.zeros(n, dtype=np.float64)
    dates: list[date] = []
    for i, row in enumerate(rows):
        dates.append(row.as_of_date)
        y[i] = _to_float(row.target_price_level)
        for j, name in enumerate(feature_names):
            if name == SPOT_FEATURE_NAME:
                X[i, j] = _to_float(row.spot_price_level)
            else:
                val = _numeric_feature_value(row.features.get(name))
                X[i, j] = 0.0 if val is None else val
    return tuple(dates), X, y


def from_build_result(
    result: BuildResult,
    *,
    horizon_days: int = 30,
) -> ForecastTrainingDataset:
    """Materialize training arrays from a PI10 ``BuildResult``."""
    if horizon_days not in FORECAST_HORIZONS:
        msg = f"unsupported horizon_days={horizon_days}"
        raise ValueError(msg)
    rows = _rows_for_horizon(result, horizon_days)
    if not rows:
        msg = f"no rows for horizon {horizon_days}d"
        raise ValueError(msg)
    ordered = tuple(sorted(rows, key=lambda r: r.as_of_date))
    feature_names = _feature_names_from_rows(ordered)
    dates, X, y = _matrix_from_rows(ordered, feature_names)
    return ForecastTrainingDataset(
        horizon_days=horizon_days,
        commodity_id=ordered[0].commodity_id,
        as_of_dates=dates,
        feature_names=feature_names,
        X=X,
        y=y,
        mode=result.metadata.mode,
    )


def load_fixture_training_dataset(
    *,
    horizon_days: int = 30,
    window_start: date | None = None,
    window_end: date | None = None,
) -> ForecastTrainingDataset:
    """CI-safe loader: PI10 fixture prices + snapshots, no database."""
    _ = FIXTURE_TRAINING_SEED
    result = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=window_start or FIXTURE_WINDOW_START,
        window_end=window_end or FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    return from_build_result(result, horizon_days=horizon_days)


def load_database_training_dataset(
    session: Session,
    *,
    horizon_days: int = 30,
    window_start: date,
    window_end: date,
    commodity_id: str | None = None,
) -> ForecastTrainingDataset:
    """Load training data from validated observations + signal snapshots."""
    builder = ForecastDatasetBuilder(session)
    if commodity_id is None:
        result = builder.build_from_database(
            window_start=window_start,
            window_end=window_end,
            horizons=(horizon_days,),
        )
    else:
        result = builder.build_from_database(
            commodity_id=commodity_id,
            window_start=window_start,
            window_end=window_end,
            horizons=(horizon_days,),
        )
    return from_build_result(result, horizon_days=horizon_days)
