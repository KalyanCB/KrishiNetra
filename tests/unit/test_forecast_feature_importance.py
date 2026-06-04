"""PI11 Track C — Random Forest feature importance tests."""

from __future__ import annotations

import json

from tests.fixtures.forecast_datasets import FIXTURE_WINDOW_DAYS, FIXTURE_WINDOW_END

from forecasting.datasets.fixtures import FIXTURE_WINDOW_START
from forecasting.features.importance import (
    build_fixture_panel,
    coerce_feature_value,
    run_feature_importance_analysis,
)
from forecasting.features.lineage import (
    feature_lineage_prefix,
    group_importances,
    top_features_per_group,
)
from forecasting.features.report import render_feature_importance_report
from forecasting.models.baselines import BASELINE_MODEL_SEED, RANDOM_FOREST_ESTIMATORS
from shared.domain.enums import Direction


def test_rf_baseline_constants() -> None:
    assert BASELINE_MODEL_SEED == 42
    assert RANDOM_FOREST_ESTIMATORS == 50


def test_feature_lineage_prefix() -> None:
    assert feature_lineage_prefix("market.direction") == "market"
    assert feature_lineage_prefix("weather.components.rainfall_deviation") == "weather"
    assert feature_lineage_prefix("futures.value") == "futures"
    assert feature_lineage_prefix("signal_market_confidence") is None


def test_coerce_direction_encoding() -> None:
    assert coerce_feature_value(Direction.BULLISH.value) == 1.0
    assert coerce_feature_value(Direction.BEARISH.value) == -1.0
    assert coerce_feature_value(Direction.NEUTRAL.value) == 0.0


def test_fixture_panel_row_count_matches_horizon_30() -> None:
    panel = build_fixture_panel(horizon_days=30)
    expected = FIXTURE_WINDOW_DAYS - 30
    assert len(panel) == expected
    assert panel[0].as_of_date == FIXTURE_WINDOW_START
    assert panel[-1].as_of_date <= FIXTURE_WINDOW_END
    assert any(name.startswith("market.") for name in panel[0].feature_values)
    assert any(name.startswith("weather.") for name in panel[0].feature_values)
    assert any(name.startswith("futures.") for name in panel[0].feature_values)


def test_run_analysis_is_deterministic() -> None:
    panel = build_fixture_panel(horizon_days=30)
    first = run_feature_importance_analysis(panel, horizon_days=30)
    second = run_feature_importance_analysis(panel, horizon_days=30)
    assert first.importances == second.importances
    assert first.top_per_group == second.top_per_group
    assert first.group_totals == second.group_totals


def test_top_features_per_group_all_lineage_prefixes() -> None:
    panel = build_fixture_panel(horizon_days=30)
    result = run_feature_importance_analysis(panel, horizon_days=30, top_k=5)
    for prefix in ("market", "weather", "futures"):
        assert prefix in result.top_per_group
        assert len(result.top_per_group[prefix]) <= 5
        for name, score in result.top_per_group[prefix]:
            assert name.startswith(f"{prefix}.")
            assert score >= 0.0


def test_group_importances_sorted_desc() -> None:
    importances = {
        "market.a": 0.1,
        "market.b": 0.3,
        "weather.x": 0.2,
    }
    grouped = group_importances(importances)
    assert grouped["market"][0] == ("market.b", 0.3)
    assert grouped["market"][1] == ("market.a", 0.1)


def test_top_features_per_group_truncates() -> None:
    grouped = {
        "market": tuple((f"market.f{i}", float(i)) for i in range(12)),
        "weather": (),
        "futures": (),
    }
    tops = top_features_per_group(grouped, top_k=3)
    assert len(tops["market"]) == 3


def test_render_report_contains_groups() -> None:
    panel = build_fixture_panel(horizon_days=30)
    result = run_feature_importance_analysis(panel, horizon_days=30)
    body = render_feature_importance_report(result, workspace_ref="testref")
    assert "PI11 Track C" in body
    assert "### Market features" in body
    assert "### Weather features" in body
    assert "### Futures features" in body
    assert "`testref`" in body


def test_report_detail_json_roundtrip() -> None:
    panel = build_fixture_panel(horizon_days=60)
    result = run_feature_importance_analysis(panel, horizon_days=60)
    payload = result.to_report_detail()
    text = json.dumps(payload)
    loaded = json.loads(text)
    assert loaded["horizon_days"] == 60
    assert "market" in loaded["top_per_group"]
