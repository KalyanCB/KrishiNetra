"""Wire PI11 Track A ``baseline_metrics.json`` into quality + registry services."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.persistence.models.forecast import ForecastModelRegistryModel
from backend.app.persistence.models.forecast_quality import ForecastQualityMetricModel
from backend.app.services.forecast.quality.metrics import HorizonQualityMetrics
from backend.app.services.forecast.quality.service import (
    ForecastQualityResult,
    ForecastQualityService,
)
from backend.app.services.forecast.registry.service import ForecastModelRegistryService
from backend.app.services.forecast.registry.types import (
    ForecastModelMetrics,
    TrainingWindow,
)
from forecasting.datasets.fixtures import FIXTURE_REGISTRY_ID
from forecasting.datasets.training import (
    ForecastTrainingDataset,
    load_fixture_training_dataset,
)

DEFAULT_BASELINE_METRICS_PATH = (
    Path(__file__).resolve().parents[4]
    / "data"
    / "forecast_models"
    / "baseline_metrics.json"
)
BASELINE_ASSESSMENT_SOURCE = "baseline_rolling_oos"
COTTON_COMMODITY_ID = "cotton"


@dataclass(frozen=True, slots=True)
class BaselineMetricsRow:
    """One Track A rolling OOS metrics row from ``baseline_metrics.json``."""

    model_name: str
    horizon_days: int
    mae: float
    rmse: float
    mape: float
    n_samples: int
    mode: str
    fold_count: int
    model_path: str | None


def model_version_for_baseline(model_name: str, *, mode: str) -> str:
    return f"{model_name}@pi11-{mode}-seed42"


def feature_set_hash_for_training(dataset: ForecastTrainingDataset) -> str:
    payload = ",".join(dataset.feature_names)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def training_window_for_dataset(dataset: ForecastTrainingDataset) -> TrainingWindow:
    return TrainingWindow(
        start=min(dataset.as_of_dates),
        end=max(dataset.as_of_dates),
    )


def load_baseline_metrics(
    path: Path | None = None,
) -> tuple[BaselineMetricsRow, ...]:
    metrics_path = path or DEFAULT_BASELINE_METRICS_PATH
    raw = json.loads(metrics_path.read_text(encoding="utf-8"))
    rows: list[BaselineMetricsRow] = []
    for entry in raw:
        metrics = entry["metrics"]
        rows.append(
            BaselineMetricsRow(
                model_name=str(entry["model_name"]),
                horizon_days=int(entry["horizon_days"]),
                mae=float(metrics["mae"]),
                rmse=float(metrics["rmse"]),
                mape=float(metrics["mape_pct"]),
                n_samples=int(metrics["n_samples"]),
                mode=str(entry.get("mode", "fixture")),
                fold_count=int(entry.get("fold_count", 0)),
                model_path=entry.get("model_path"),
            )
        )
    return tuple(rows)


def quality_result_from_baseline_row(
    row: BaselineMetricsRow,
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
) -> ForecastQualityResult:
    """Build a ``ForecastQualityResult`` from Track A aggregate OOS metrics."""
    horizon_metrics = HorizonQualityMetrics(
        horizon_days=row.horizon_days,
        sample_count=row.n_samples,
        mae=row.mae,
        rmse=row.rmse,
        mape=row.mape,
        coverage=None,
    )
    return ForecastQualityResult(
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry_id=registry_id,
        model_version=model_version_for_baseline(row.model_name, mode=row.mode),
        assessment_source=BASELINE_ASSESSMENT_SOURCE,
        by_horizon={row.horizon_days: horizon_metrics},
        sample_count_total=row.n_samples,
    )


class BaselineHandoffService:
    """Register Track A baselines and persist rolling OOS KPIs."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._quality = ForecastQualityService(session)
        self._registry = ForecastModelRegistryService(session)

    def sync_from_metrics_json(
        self,
        *,
        metrics_path: Path | None = None,
        commodity_id: str = COTTON_COMMODITY_ID,
        registry_id: UUID = FIXTURE_REGISTRY_ID,
        as_of_date: date | None = None,
        dataset: ForecastTrainingDataset | None = None,
        feature_set_hash: str | None = None,
    ) -> tuple[
        tuple[ForecastModelRegistryModel, ...],
        list[ForecastQualityMetricModel],
    ]:
        """
        Load ``baseline_metrics.json``, register each model, persist quality KPIs.

        Uses fixture training metadata (window, feature hash) when ``dataset`` is omitted.
        """
        rows = load_baseline_metrics(metrics_path)
        train_dataset = dataset or load_fixture_training_dataset(horizon_days=30)
        window = training_window_for_dataset(train_dataset)
        fhash = feature_set_hash or feature_set_hash_for_training(train_dataset)
        quality_as_of = as_of_date or window.end

        registered: list[ForecastModelRegistryModel] = []
        quality_rows: list[ForecastQualityMetricModel] = []

        for row in rows:
            version = model_version_for_baseline(row.model_name, mode=row.mode)
            registry_entry = self._registry.register(
                commodity_id=commodity_id,
                registry_id=registry_id,
                model_version=version,
                model_family=row.model_name,
                training_window=window,
                metrics=ForecastModelMetrics(
                    mae=row.mae,
                    rmse=row.rmse,
                    mape=row.mape,
                    horizon_days=row.horizon_days,
                ),
                feature_set_hash=fhash,
            )
            registered.append(registry_entry)

            result = quality_result_from_baseline_row(
                row,
                commodity_id=commodity_id,
                as_of_date=quality_as_of,
                registry_id=registry_id,
            )
            quality_rows.extend(self._quality.persist(result))

        return tuple(registered), quality_rows


__all__ = [
    "BASELINE_ASSESSMENT_SOURCE",
    "BaselineHandoffService",
    "BaselineMetricsRow",
    "COTTON_COMMODITY_ID",
    "DEFAULT_BASELINE_METRICS_PATH",
    "feature_set_hash_for_training",
    "load_baseline_metrics",
    "model_version_for_baseline",
    "quality_result_from_baseline_row",
    "training_window_for_dataset",
]
