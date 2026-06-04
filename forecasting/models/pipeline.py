"""Train and evaluate PI11 baseline models on rolling held-out windows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
from numpy.typing import NDArray

from forecasting.backtest.rolling import (
    DEFAULT_MIN_TRAIN_SIZE,
    DEFAULT_STEP,
    DEFAULT_TEST_SIZE,
    collect_out_of_sample_predictions,
)
from forecasting.datasets.training import ForecastTrainingDataset
from forecasting.models.baselines import BASELINE_MODEL_NAMES, build_baseline_model
from forecasting.models.metrics import RegressionMetrics, regression_metrics

DEFAULT_MODELS_DIR = Path("data/forecast_models")


@dataclass(frozen=True, slots=True)
class BaselineEvaluationResult:
    model_name: str
    horizon_days: int
    metrics: RegressionMetrics
    model_path: Path | None
    fold_count: int
    mode: str

    def to_dict(self) -> dict[str, object]:
        return {
            "model_name": self.model_name,
            "horizon_days": self.horizon_days,
            "metrics": self.metrics.to_dict(),
            "model_path": str(self.model_path) if self.model_path else None,
            "fold_count": self.fold_count,
            "mode": self.mode,
        }


def _evaluate_model_rolling(
    dataset: ForecastTrainingDataset,
    model_name: str,
    *,
    min_train_size: int = DEFAULT_MIN_TRAIN_SIZE,
    test_size: int = DEFAULT_TEST_SIZE,
    step: int | None = DEFAULT_STEP,
) -> tuple[RegressionMetrics, int]:
    model = build_baseline_model(model_name, feature_names=dataset.feature_names)
    fold_count = 0

    def fit_predict_fold(
        train_idx: NDArray[np.int64],
        test_idx: NDArray[np.int64],
    ) -> NDArray[np.float64]:
        nonlocal fold_count
        fold_count += 1
        model.fit(dataset.X[train_idx], dataset.y[train_idx])
        return model.predict(dataset.X[test_idx])

    y_true, y_pred = collect_out_of_sample_predictions(
        dataset.y,
        min_train_size=min_train_size,
        test_size=test_size,
        step=step,
        fit_predict_fold=fit_predict_fold,
    )
    return regression_metrics(y_true, y_pred), fold_count


def _artifact_directory(
    output_dir: Path,
    horizon_days: int,
    *,
    use_horizon_subdir: bool,
) -> Path:
    path = output_dir / f"{horizon_days}d" if use_horizon_subdir else output_dir
    path.mkdir(parents=True, exist_ok=True)
    return path


def train_full_corpus_and_save(
    dataset: ForecastTrainingDataset,
    model_name: str,
    output_dir: Path,
    *,
    use_horizon_subdir: bool = True,
) -> Path:
    """Fit on full corpus and persist with joblib (artifact for inspection, not OOS metrics)."""
    model = build_baseline_model(model_name, feature_names=dataset.feature_names)
    model.fit(dataset.X, dataset.y)
    horizon_dir = _artifact_directory(
        output_dir,
        dataset.horizon_days,
        use_horizon_subdir=use_horizon_subdir,
    )
    path = horizon_dir / f"{model_name}.joblib"
    joblib.dump(
        {
            "model": model,
            "feature_names": dataset.feature_names,
            "horizon_days": dataset.horizon_days,
            "commodity_id": dataset.commodity_id,
        },
        path,
    )
    return path


def best_non_naive_beats_naive(
    results: tuple[BaselineEvaluationResult, ...],
    *,
    metric: str = "rmse",
) -> bool:
    """True when any non-naive model has strictly lower ``metric`` than naive."""
    by_name = {r.model_name: r for r in results}
    naive = by_name.get("naive_persistence")
    if naive is None:
        return False
    naive_value = getattr(naive.metrics, metric)
    for name, row in by_name.items():
        if name == "naive_persistence":
            continue
        if getattr(row.metrics, metric) < naive_value:
            return True
    return False


def evaluate_all_baselines(
    dataset: ForecastTrainingDataset,
    *,
    output_dir: Path | None = None,
    save_models: bool = True,
    use_horizon_subdir: bool = True,
    min_train_size: int = DEFAULT_MIN_TRAIN_SIZE,
    test_size: int = DEFAULT_TEST_SIZE,
    step: int | None = DEFAULT_STEP,
) -> tuple[BaselineEvaluationResult, ...]:
    """Rolling-window OOS metrics + optional full-corpus model artifacts."""
    models_dir = output_dir or DEFAULT_MODELS_DIR
    results: list[BaselineEvaluationResult] = []
    for name in BASELINE_MODEL_NAMES:
        metrics, fold_count = _evaluate_model_rolling(
            dataset,
            name,
            min_train_size=min_train_size,
            test_size=test_size,
            step=step,
        )
        model_path: Path | None = None
        if save_models:
            model_path = train_full_corpus_and_save(
                dataset,
                name,
                models_dir,
                use_horizon_subdir=use_horizon_subdir,
            )
        results.append(
            BaselineEvaluationResult(
                model_name=name,
                horizon_days=dataset.horizon_days,
                metrics=metrics,
                model_path=model_path,
                fold_count=fold_count,
                mode=dataset.mode,
            )
        )
    return tuple(results)


def export_metrics_json(
    results: tuple[BaselineEvaluationResult, ...],
    path: Path,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [r.to_dict() for r in results]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
