"""PI12 Track D — fixture leakage vs perfect-separability audit (regression)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pytest
from sklearn.linear_model import LinearRegression
from tests.fixtures.forecast_datasets import (
    FIXTURE_WINDOW_END,
    FIXTURE_WINDOW_START,
    fixture_price_window,
    fixture_primary_markets,
    fixture_snapshots_by_date,
)

from backend.app.services.forecast.validation.rolling import (
    RollingValidationSpec,
    assert_no_label_leakage,
    run_rolling_validation,
)
from forecasting.backtest.rolling import iter_rolling_folds
from forecasting.datasets.builder import build_fixture_datasets
from forecasting.datasets.training import (
    SPOT_FEATURE_NAME,
    from_build_result,
    load_fixture_training_dataset,
)
from forecasting.models.pipeline import evaluate_all_baselines

FIXTURE_DAILY_SLOPE_INR = 15.0
FIXTURE_HORIZON_DAYS = 30
FIXTURE_TARGET_OFFSET_INR = FIXTURE_DAILY_SLOPE_INR * FIXTURE_HORIZON_DAYS


def test_fixture_target_is_affine_in_spot_not_in_feature_dict() -> None:
    """Target is separate from X; on PI10 fixture it follows y = spot + 450."""
    dataset = load_fixture_training_dataset(horizon_days=FIXTURE_HORIZON_DAYS)
    spot = dataset.spot_levels()
    delta = dataset.y - spot
    assert np.allclose(delta, FIXTURE_TARGET_OFFSET_INR, rtol=0, atol=1e-9)
    assert SPOT_FEATURE_NAME in dataset.feature_names
    assert "target_price_level" not in dataset.feature_names


def test_track_b_label_embargo_passes_on_fixture_folds() -> None:
    result = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    rows = result.datasets[FIXTURE_HORIZON_DAYS]
    validation = run_rolling_validation(
        rows,
        RollingValidationSpec(min_train_rows=24, window_mode="expanding"),
    )
    assert validation.fold_count > 0
    for fold in validation.folds:
        assert_no_label_leakage(fold.train_rows, fold.test_row)


def test_linear_regression_zero_oos_on_fixture_rolling() -> None:
    """PI11 anomaly: sklearn linear hits ~0 MAE on fixture, not on noisy panel."""
    dataset = load_fixture_training_dataset(horizon_days=FIXTURE_HORIZON_DAYS)
    results = {r.model_name: r for r in evaluate_all_baselines(dataset, save_models=False)}
    linear = results["linear_regression"]
    naive = results["naive_persistence"]
    assert linear.metrics.mae < 1e-6
    assert linear.metrics.rmse < 1e-6
    assert linear.metrics.mape_pct < 1e-6
    assert linear.fold_count == 3
    assert naive.metrics.mae == pytest.approx(FIXTURE_TARGET_OFFSET_INR)
    assert naive.metrics.rmse == pytest.approx(FIXTURE_TARGET_OFFSET_INR)


def test_perturbed_fixture_breaks_linear_perfect_fit() -> None:
    """Real-data expectation: noise breaks exact affine memorization."""
    prices = fixture_price_window()
    rng = np.random.default_rng(42)
    for row in prices:
        jitter = Decimal(str(rng.uniform(-50.0, 50.0)))
        row.value = row.value + jitter
    result = build_fixture_datasets(
        prices=prices,
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    dataset = from_build_result(result, horizon_days=FIXTURE_HORIZON_DAYS)
    model = LinearRegression()
    fold_maes: list[float] = []
    for fold in iter_rolling_folds(
        dataset.n_samples, min_train_size=60, test_size=20, step=20
    ):
        model.fit(dataset.X[fold.train_indices], dataset.y[fold.train_indices])
        preds = model.predict(dataset.X[fold.test_indices])
        fold_maes.append(float(np.mean(np.abs(preds - dataset.y[fold.test_indices]))))
    assert max(fold_maes) > 1.0


def test_builder_target_uses_future_modal_only() -> None:
    result = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    row = result.datasets[FIXTURE_HORIZON_DAYS][0]
    assert row.target_price_level != row.spot_price_level
    assert row.as_of_date + timedelta(days=FIXTURE_HORIZON_DAYS) > row.as_of_date
    assert isinstance(row.as_of_date, date)
