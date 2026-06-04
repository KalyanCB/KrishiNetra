"""PI10 Track E: signal effectiveness correlation tests."""

from __future__ import annotations

from datetime import date

import pytest
from tests.fixtures.signal_effectiveness import build_synthetic_observation_panel

from backend.app.services.research.signal_effectiveness.analysis import (
    run_signal_effectiveness_analysis,
)
from backend.app.services.research.signal_effectiveness.metrics import (
    compute_pct_forward_return,
    correlate_series,
    pearson_r,
    pick_best_worst,
    spearman_rho,
)
from backend.app.services.research.signal_effectiveness.panel import build_daily_panel
from backend.app.services.research.signal_effectiveness.report import (
    render_signal_effectiveness_report_markdown,
)


def test_pearson_perfect_positive() -> None:
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [2.0, 4.0, 6.0, 8.0, 10.0]
    assert pearson_r(xs, ys) == pytest.approx(1.0)


def test_pearson_zero_variance_returns_none() -> None:
    assert pearson_r([1.0, 1.0, 1.0], [2.0, 3.0, 4.0]) is None


def test_spearman_monotonic() -> None:
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [10.0, 20.0, 30.0, 40.0, 50.0]
    assert spearman_rho(xs, ys) == pytest.approx(1.0)


def test_forward_return_pct() -> None:
    assert compute_pct_forward_return(price_today=7000.0, price_future=7140.0) == pytest.approx(
        0.02
    )
    assert compute_pct_forward_return(price_today=0.0, price_future=100.0) is None


def test_correlate_series_sample_size() -> None:
    result = correlate_series(
        signal="price_momentum",
        horizon_days=7,
        signal_values=[1.0, 2.0, 3.0, 4.0],
        forward_returns=[0.01, 0.02, 0.03, 0.04],
    )
    assert result.sample_size == 4
    assert result.pearson_r == pytest.approx(1.0)


def test_pick_best_worst_by_absolute_r() -> None:
    results = (
        correlate_series(
            signal="price_momentum",
            horizon_days=30,
            signal_values=[1.0, 2.0, 3.0, 4.0, 5.0],
            forward_returns=[0.01, 0.02, 0.03, 0.04, 0.05],
        ),
        correlate_series(
            signal="rainfall_shock",
            horizon_days=30,
            signal_values=[0.1, 0.2, 0.3, 0.4, 0.5],
            forward_returns=[0.05, 0.04, 0.03, 0.02, 0.01],
        ),
    )
    best, worst = pick_best_worst(results, horizon_days=30)
    assert best is not None
    assert worst is not None
    assert best.signal == "price_momentum"
    assert worst.signal == "rainfall_shock"


def test_synthetic_panel_produces_evaluable_rows() -> None:
    panel = build_synthetic_observation_panel(
        window_start=date(2024, 11, 1),
        window_end=date(2025, 8, 31),
    )
    rows = build_daily_panel(panel)
    assert len(rows) >= 100
    assert rows[0].price_momentum is not None
    assert rows[0].forward_return_7d is not None
    assert rows[0].forward_return_30d is not None


def test_run_analysis_on_fixture() -> None:
    panel = build_synthetic_observation_panel(
        window_start=date(2024, 11, 1),
        window_end=date(2025, 8, 31),
    )
    result = run_signal_effectiveness_analysis(panel)
    assert result.price_observation_count > 0
    assert result.panel_summary["evaluable_days"] >= 100
    assert len(result.correlations) == 8
    assert result.best_signal is not None
    assert result.worst_signal is not None
    assert all(c.sample_size >= 3 for c in result.correlations)


def test_render_report_contains_track_header() -> None:
    panel = build_synthetic_observation_panel(
        window_start=date(2024, 11, 1),
        window_end=date(2025, 5, 31),
    )
    result = run_signal_effectiveness_analysis(panel)
    body = render_signal_effectiveness_report_markdown(result=result)
    assert "Signal Effectiveness Report — PI10 Track E" in body
    assert "price_momentum" in body
    assert "rainfall_shock" in body
