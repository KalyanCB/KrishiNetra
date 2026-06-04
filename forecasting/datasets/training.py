"""PI11 Track A — supervised training matrices from PI10 forecast datasets."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import numpy as np
from numpy.typing import NDArray
from sqlalchemy.orm import Session

from forecasting.datasets.builder import (
    FORECAST_HORIZONS,
    BuildMetadata,
    BuildResult,
    ForecastDatasetBuilder,
    ForecastDatasetRow,
    HorizonDatasetStats,
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
DEFAULT_REAL_DATASET_DIR = Path("data/forecast_datasets")
REAL_JSONL_PREFIX = "real_"
JSONL_CORE_KEYS = frozenset(
    {
        "as_of_date",
        "commodity_id",
        "horizon_days",
        "spot_price_level",
        "target_price_level",
        "target_log_return",
        "registry_id",
        "snapshot_hash",
    }
)


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


def _parse_decimal_field(value: object, field: str) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        return Decimal(value)
    msg = f"{field} must be numeric string or number, got {type(value).__name__}"
    raise ValueError(msg)


def row_from_jsonl_record(record: dict[str, object]) -> ForecastDatasetRow:
    """Parse one exported JSONL line into a ``ForecastDatasetRow``."""
    as_of_raw = record["as_of_date"]
    if not isinstance(as_of_raw, str):
        msg = "as_of_date must be ISO date string"
        raise ValueError(msg)
    horizon_raw = record.get("horizon_days", 30)
    if isinstance(horizon_raw, int):
        horizon_days = horizon_raw
    elif horizon_raw is None:
        horizon_days = 30
    else:
        horizon_days = int(str(horizon_raw))
    commodity_raw = record.get("commodity_id", "cotton")
    commodity_id = str(commodity_raw) if commodity_raw is not None else "cotton"
    spot = _parse_decimal_field(record["spot_price_level"], "spot_price_level")
    target = _parse_decimal_field(record["target_price_level"], "target_price_level")
    log_return_raw = record.get("target_log_return", 0.0)
    if isinstance(log_return_raw, (int, float)):
        target_log_return = float(log_return_raw)
    elif log_return_raw is None:
        target_log_return = 0.0
    else:
        target_log_return = float(str(log_return_raw))
    registry_id: UUID | None = None
    if "registry_id" in record and record["registry_id"] is not None:
        registry_id = UUID(str(record["registry_id"]))
    snapshot_hash = (
        str(record["snapshot_hash"]) if record.get("snapshot_hash") is not None else None
    )
    features: dict[str, object] = {
        k: v for k, v in record.items() if k not in JSONL_CORE_KEYS
    }
    return ForecastDatasetRow(
        as_of_date=date.fromisoformat(as_of_raw),
        commodity_id=commodity_id,
        horizon_days=horizon_days,
        spot_price_level=spot,
        target_price_level=target,
        target_log_return=target_log_return,
        registry_id=registry_id,
        snapshot_hash=snapshot_hash,
        features=features,
    )


def load_jsonl_rows(path: Path) -> tuple[ForecastDatasetRow, ...]:
    if not path.is_file():
        msg = f"JSONL corpus not found: {path}"
        raise FileNotFoundError(msg)
    rows: list[ForecastDatasetRow] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                msg = f"invalid JSON at {path}:{line_no}"
                raise ValueError(msg) from exc
            if not isinstance(record, dict):
                msg = f"JSONL row must be object at {path}:{line_no}"
                raise ValueError(msg)
            rows.append(row_from_jsonl_record(record))
    if not rows:
        msg = f"no rows in {path}"
        raise ValueError(msg)
    return tuple(rows)


def build_result_from_jsonl_rows(
    rows: tuple[ForecastDatasetRow, ...],
    *,
    horizon_days: int,
    mode: str = "real",
) -> BuildResult:
    """Wrap parsed JSONL rows in a ``BuildResult`` for ``from_build_result``."""
    if horizon_days not in FORECAST_HORIZONS:
        msg = f"unsupported horizon_days={horizon_days}"
        raise ValueError(msg)
    horizon_rows = tuple(r for r in rows if r.horizon_days == horizon_days)
    if not horizon_rows:
        msg = f"no rows for horizon {horizon_days}d in JSONL corpus"
        raise ValueError(msg)
    ordered = tuple(sorted(horizon_rows, key=lambda r: r.as_of_date))
    dates = [r.as_of_date for r in ordered]
    return BuildResult(
        datasets={horizon_days: ordered},
        stats={
            horizon_days: HorizonDatasetStats(
                horizon_days=horizon_days,
                row_count=len(ordered),
                candidate_dates=len(ordered),
                coverage_ratio=1.0,
                missing_by_field={},
            )
        },
        metadata=BuildMetadata(
            mode=mode,
            commodity_id=ordered[0].commodity_id,
            window_start=min(dates),
            window_end=max(dates),
            primary_market_count=0,
            spot_dates=len(ordered),
        ),
    )


def real_forecast_jsonl_path(
    horizon_days: int,
    *,
    dataset_dir: Path | None = None,
    filename_prefix: str = REAL_JSONL_PREFIX,
) -> Path:
    base = dataset_dir or DEFAULT_REAL_DATASET_DIR
    return base / f"{filename_prefix}forecast_target_{horizon_days}d.jsonl"


def load_real_training_dataset(
    *,
    horizon_days: int = 30,
    dataset_dir: Path | None = None,
    filename_prefix: str = REAL_JSONL_PREFIX,
) -> ForecastTrainingDataset:
    """PI12 Track C — train only on exported @5433 corpus (no fixture, no live DB)."""
    path = real_forecast_jsonl_path(
        horizon_days,
        dataset_dir=dataset_dir,
        filename_prefix=filename_prefix,
    )
    rows = load_jsonl_rows(path)
    result = build_result_from_jsonl_rows(rows, horizon_days=horizon_days, mode="real")
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
