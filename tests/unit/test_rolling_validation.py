"""PI11 Track B — rolling / expanding walk-forward validation (no leakage)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from tests.fixtures.forecast_datasets import (
    FIXTURE_WINDOW_END,
    FIXTURE_WINDOW_START,
    fixture_price_window,
    fixture_primary_markets,
    fixture_snapshots_by_date,
)

from backend.app.services.forecast.validation.rolling import (
    DEFAULT_PRIMARY_HORIZON_DAYS,
    RollingValidationError,
    RollingValidationSpec,
    assert_no_label_leakage,
    build_rolling_folds,
    dataset_rows_from_pi10_fixture,
    label_realization_date,
    render_time_series_validation_report,
    run_rolling_validation,
)
from forecasting.datasets.builder import (
    FORECAST_HORIZONS,
    ForecastDatasetRow,
    build_fixture_datasets,
)


def _row(as_of: date, *, horizon: int = 30) -> ForecastDatasetRow:
    spot = Decimal("7000")
    target = Decimal("7100")
    return ForecastDatasetRow(
        as_of_date=as_of,
        commodity_id="cotton",
        horizon_days=horizon,
        spot_price_level=spot,
        target_price_level=target,
        target_log_return=0.01,
        registry_id=None,
        snapshot_hash=None,
        features={},
    )


def test_primary_horizon_is_30d() -> None:
    assert DEFAULT_PRIMARY_HORIZON_DAYS == 30
    assert DEFAULT_PRIMARY_HORIZON_DAYS in FORECAST_HORIZONS


def test_label_realization_date() -> None:
    row = _row(date(2026, 1, 1), horizon=30)
    assert label_realization_date(row) == date(2026, 1, 31)


def test_assert_no_label_leakage_rejects_overlapping_target() -> None:
    test = _row(date(2026, 3, 1))
    train = _row(date(2026, 2, 15))  # label 2026-03-17 >= test as_of
    with pytest.raises(RollingValidationError, match="label leakage"):
        assert_no_label_leakage([train], test)


def test_assert_no_label_leakage_accepts_safe_train() -> None:
    test = _row(date(2026, 3, 15))
    safe = _row(date(2026, 1, 1))  # label 2026-01-31
    assert_no_label_leakage([safe], test)


def test_build_folds_are_strictly_chronological() -> None:
    rows = tuple(_row(date(2026, 1, 1) + timedelta(days=i)) for i in range(80))
    spec = RollingValidationSpec(min_train_rows=10, step_rows=1)
    folds = build_rolling_folds(rows, spec)
    dates = [f.test_as_of_date for f in folds]
    assert dates == sorted(dates)
    assert len(folds) > 0


def test_no_future_labels_in_train_window_per_fold() -> None:
    rows = dataset_rows_from_pi10_fixture(horizon_days=30)
    result = run_rolling_validation(
        rows,
        RollingValidationSpec(min_train_rows=24, window_mode="expanding"),
    )
    assert result.fold_count > 0
    for fold in result.folds:
        assert_no_label_leakage(fold.train_rows, fold.test_row)
        for train in fold.train_rows:
            assert train.as_of_date < fold.test_as_of_date
            assert label_realization_date(train) < fold.test_as_of_date


def test_expanding_train_grows_with_later_folds() -> None:
    rows = dataset_rows_from_pi10_fixture()
    spec = RollingValidationSpec(min_train_rows=24, window_mode="expanding")
    folds = build_rolling_folds(rows, spec)
    sizes = [len(f.train_rows) for f in folds]
    assert sizes[-1] >= sizes[0]
    assert sizes == sorted(sizes)


def test_sliding_train_capped_by_window() -> None:
    rows = dataset_rows_from_pi10_fixture()
    window = 30
    spec = RollingValidationSpec(
        min_train_rows=24,
        window_mode="sliding",
        train_window_rows=window,
    )
    folds = build_rolling_folds(rows, spec)
    assert folds
    assert all(len(f.train_rows) <= window for f in folds)


def test_step_rows_reduces_fold_count() -> None:
    rows = dataset_rows_from_pi10_fixture()
    all_folds = build_rolling_folds(
        rows, RollingValidationSpec(min_train_rows=24, step_rows=1)
    )
    stepped = build_rolling_folds(
        rows, RollingValidationSpec(min_train_rows=24, step_rows=5)
    )
    assert len(stepped) < len(all_folds)


def test_pi10_fixture_integration_row_count() -> None:
    rows = dataset_rows_from_pi10_fixture(horizon_days=30)
    assert len(rows) == 120
    assert rows[0].horizon_days == 30


def test_duplicate_as_of_rejected() -> None:
    rows = (_row(date(2026, 1, 1)), _row(date(2026, 1, 1)))
    with pytest.raises(RollingValidationError, match="duplicate"):
        build_rolling_folds(rows, RollingValidationSpec(min_train_rows=1))


def test_sliding_spec_requires_train_window_rows() -> None:
    with pytest.raises(RollingValidationError, match="train_window_rows"):
        RollingValidationSpec(window_mode="sliding")


def test_report_renders_with_fixture_run() -> None:
    rows = dataset_rows_from_pi10_fixture()
    result = run_rolling_validation(rows)
    body = render_time_series_validation_report(result, workspace_ref="2fb4e5b")
    assert "PI11 Track B" in body
    assert "30d" in body
    assert "no random" in body.lower() or "no random splits" in body.lower()


def test_build_fixture_datasets_matches_pi10_loader() -> None:
    direct = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    ).datasets[30]
    loaded = dataset_rows_from_pi10_fixture()
    assert [r.as_of_date for r in direct] == [r.as_of_date for r in loaded]
