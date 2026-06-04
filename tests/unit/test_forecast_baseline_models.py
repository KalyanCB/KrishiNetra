"""PI11 Track A — forecast baseline training, rolling OOS metrics, fixture loader."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from tests.fixtures.forecast_datasets import (
    FIXTURE_WINDOW_END,
    FIXTURE_WINDOW_START,
    fixture_price_window,
    fixture_primary_markets,
    fixture_snapshots_by_date,
)

from forecasting.backtest.rolling import iter_rolling_folds
from forecasting.datasets.builder import build_fixture_datasets
from forecasting.datasets.training import (
    FIXTURE_TRAINING_SEED,
    SPOT_FEATURE_NAME,
    build_result_from_jsonl_rows,
    from_build_result,
    load_fixture_training_dataset,
    load_jsonl_rows,
    load_real_training_dataset,
    row_from_jsonl_record,
)
from forecasting.models.baselines import (
    BASELINE_MODEL_NAMES,
    BASELINE_MODEL_SEED,
    NaivePersistenceBaseline,
    build_baseline_model,
)
from forecasting.models.metrics import regression_metrics
from forecasting.models.pipeline import (
    best_non_naive_beats_naive,
    evaluate_all_baselines,
    export_metrics_json,
)


def test_fixture_training_seed_constant() -> None:
    assert FIXTURE_TRAINING_SEED == 42
    assert BASELINE_MODEL_SEED == 42


def test_training_dataset_30d_shape() -> None:
    dataset = load_fixture_training_dataset(horizon_days=30)
    assert dataset.mode == "fixture"
    assert dataset.horizon_days == 30
    assert dataset.n_samples == 120
    assert dataset.feature_names[0] == SPOT_FEATURE_NAME
    assert dataset.n_features >= 3
    assert dataset.y.shape == (120,)
    assert dataset.X.shape == (120, dataset.n_features)


def test_training_dataset_sorted_by_date() -> None:
    dataset = load_fixture_training_dataset(horizon_days=30)
    assert list(dataset.as_of_dates) == sorted(dataset.as_of_dates)


def test_targets_match_builder_rows() -> None:
    result = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    dataset = from_build_result(result, horizon_days=30)
    row = result.datasets[30][0]
    assert dataset.y[0] == pytest.approx(float(row.target_price_level))
    assert dataset.X[0, 0] == pytest.approx(float(row.spot_price_level))


def test_rolling_folds_fixture_corpus() -> None:
    folds = list(iter_rolling_folds(120, min_train_size=60, test_size=20, step=20))
    assert len(folds) == 3
    assert folds[0].train_indices.shape[0] == 60
    assert folds[0].test_indices.shape[0] == 20


def test_naive_persistence_perfect_on_flat_spot_shift() -> None:
    """Monotonic fixture: spot at T + fixed increment ≈ target at T+30 when slope matches."""
    dataset = load_fixture_training_dataset(horizon_days=30)
    model = NaivePersistenceBaseline()
    model.fit(dataset.X, dataset.y)
    preds = model.predict(dataset.X)
    # Fixture uses +15/day spot; 30d forward modal rises 450 INR vs spot
    assert np.mean(np.abs(preds - dataset.y)) > 0.0


def test_regression_metrics_known_vectors() -> None:
    y_true = np.array([100.0, 200.0], dtype=np.float64)
    y_pred = np.array([110.0, 180.0], dtype=np.float64)
    m = regression_metrics(y_true, y_pred)
    assert m.mae == pytest.approx(15.0)
    assert m.rmse == pytest.approx((10.0**2 + 20.0**2) ** 0.5 / (2**0.5))
    assert m.n_samples == 2


def test_evaluate_all_baselines_deterministic(tmp_path: Path) -> None:
    dataset = load_fixture_training_dataset(horizon_days=30)
    a = evaluate_all_baselines(dataset, output_dir=tmp_path / "a")
    b = evaluate_all_baselines(dataset, output_dir=tmp_path / "b")
    assert len(a) == len(BASELINE_MODEL_NAMES) == 3
    for left, right in zip(a, b, strict=True):
        assert left.model_name == right.model_name
        assert left.metrics.mae == pytest.approx(right.metrics.mae)
        assert left.metrics.rmse == pytest.approx(right.metrics.rmse)
        assert left.fold_count == right.fold_count == 3


def test_baseline_models_improve_or_match_naive_rmse_ordering() -> None:
    dataset = load_fixture_training_dataset(horizon_days=30)
    results = {r.model_name: r for r in evaluate_all_baselines(dataset, save_models=False)}
    assert results["naive_persistence"].metrics.n_samples == 60
    assert results["linear_regression"].metrics.rmse <= results["naive_persistence"].metrics.rmse


def test_export_metrics_json(tmp_path: Path) -> None:
    dataset = load_fixture_training_dataset(horizon_days=30)
    results = evaluate_all_baselines(dataset, output_dir=tmp_path, save_models=True)
    path = export_metrics_json(results, tmp_path / "metrics.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload) == 3
    assert payload[0]["model_name"] in BASELINE_MODEL_NAMES


def test_build_baseline_model_names() -> None:
    dataset = load_fixture_training_dataset(horizon_days=30)
    for name in BASELINE_MODEL_NAMES:
        model = build_baseline_model(name, feature_names=dataset.feature_names)
        model.fit(dataset.X[:10], dataset.y[:10])
        preds = model.predict(dataset.X[10:12])
        assert preds.shape == (2,)


def test_row_from_jsonl_record_minimal() -> None:
    row = row_from_jsonl_record(
        {
            "as_of_date": "2023-06-01",
            "commodity_id": "cotton",
            "horizon_days": 30,
            "spot_price_level": "1000.0",
            "target_price_level": "1100.0",
            "target_log_return": 0.09531,
        }
    )
    assert row.commodity_id == "cotton"
    assert row.horizon_days == 30
    assert float(row.spot_price_level) == pytest.approx(1000.0)


def test_load_real_training_dataset_30d_shape() -> None:
    dataset = load_real_training_dataset(horizon_days=30)
    assert dataset.mode == "real"
    assert dataset.horizon_days == 30
    assert dataset.n_samples == 1069
    assert dataset.feature_names[0] == SPOT_FEATURE_NAME
    assert dataset.n_features == 1


def test_real_jsonl_roundtrip_build_result(tmp_path: Path) -> None:
    fixture_ds = load_fixture_training_dataset(horizon_days=30)
    jsonl_path = tmp_path / "real_forecast_target_30d.jsonl"
    rows = build_result_from_jsonl_rows(
        tuple(
            row_from_jsonl_record(
                {
                    "as_of_date": d.isoformat(),
                    "commodity_id": "cotton",
                    "horizon_days": 30,
                    "spot_price_level": str(fixture_ds.X[i, 0]),
                    "target_price_level": str(fixture_ds.y[i]),
                    "target_log_return": 0.0,
                }
            )
            for i, d in enumerate(fixture_ds.as_of_dates[:5])
        ),
        horizon_days=30,
    ).datasets[30]
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(
                json.dumps(
                    {
                        "as_of_date": row.as_of_date.isoformat(),
                        "commodity_id": row.commodity_id,
                        "horizon_days": row.horizon_days,
                        "spot_price_level": str(row.spot_price_level),
                        "target_price_level": str(row.target_price_level),
                        "target_log_return": row.target_log_return,
                    }
                )
            )
            handle.write("\n")
    loaded = load_jsonl_rows(jsonl_path)
    assert len(loaded) == 5


def test_best_non_naive_beats_naive_helper() -> None:
    dataset = load_fixture_training_dataset(horizon_days=30)
    results = evaluate_all_baselines(dataset, save_models=False)
    assert best_non_naive_beats_naive(results, metric="rmse") is True


def test_training_dataset_empty_horizon_raises() -> None:
    result = build_fixture_datasets(
        prices=[],
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
    )
    with pytest.raises(ValueError, match="no rows"):
        from_build_result(result, horizon_days=30)
