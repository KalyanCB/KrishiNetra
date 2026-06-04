"""PI10 Track D — forecast target dataset builder tests (fixture + validation)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest
from tests.fixtures.forecast_datasets import (
    FIXTURE_WINDOW_DAYS,
    FIXTURE_WINDOW_END,
    FIXTURE_WINDOW_START,
    fixture_price_window,
    fixture_primary_markets,
    fixture_snapshots_by_date,
)

from forecasting.datasets.basket import (
    basket_modals_by_date,
    filter_validated_primary_prices,
)
from forecasting.datasets.builder import (
    FIXTURE_RANDOM_SEED,
    FORECAST_HORIZONS,
    ForecastDatasetRow,
    build_fixture_datasets,
    export_datasets_jsonl,
)


def test_fixture_seed_constant() -> None:
    assert FIXTURE_RANDOM_SEED == 42


def test_fixture_build_row_counts_per_horizon() -> None:
    result = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    assert result.metadata.mode == "fixture"
    assert result.metadata.spot_dates == FIXTURE_WINDOW_DAYS
    expected_30 = FIXTURE_WINDOW_DAYS - 30
    expected_60 = FIXTURE_WINDOW_DAYS - 60
    expected_90 = FIXTURE_WINDOW_DAYS - 90
    assert result.stats[30].row_count == expected_30
    assert result.stats[60].row_count == expected_60
    assert result.stats[90].row_count == expected_90
    assert result.stats[30].coverage_ratio == pytest.approx(1.0)
    assert result.stats[30].missing_by_field.get("spot_price_level", 0) == 0
    assert result.stats[30].missing_by_field.get("target_price_level", 0) == 0


def test_targets_use_future_modal_without_leakage() -> None:
    prices = fixture_price_window()
    filtered = filter_validated_primary_prices(prices, fixture_primary_markets())
    modals = basket_modals_by_date(filtered)
    result = build_fixture_datasets(
        prices=prices,
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    sample = result.datasets[30][0]
    target_date = sample.as_of_date + timedelta(days=30)
    assert sample.target_price_level == modals[target_date]
    assert sample.spot_price_level == modals[sample.as_of_date]


def test_log_return_matches_price_ratio() -> None:
    result = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    row = result.datasets[60][10]
    ratio = float(row.target_price_level) / float(row.spot_price_level)
    assert row.target_log_return == pytest.approx(__import__("math").log(ratio), rel=1e-6)


def test_snapshot_features_attached() -> None:
    result = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    row = result.datasets[90][0]
    assert row.snapshot_hash is not None
    assert any(key.endswith("_confidence") for key in row.features)


def test_export_jsonl_roundtrip(tmp_path) -> None:
    result = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    paths = export_datasets_jsonl(result, tmp_path)
    assert set(paths) == set(FORECAST_HORIZONS)
    for horizon in FORECAST_HORIZONS:
        lines = paths[horizon].read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == result.stats[horizon].row_count
        first = json.loads(lines[0])
        assert first["horizon_days"] == horizon
        assert "target_price_level" in first


def test_build_reproducible_across_runs() -> None:
    kwargs = {
        "prices": fixture_price_window(),
        "snapshots_by_date": fixture_snapshots_by_date(),
        "window_start": FIXTURE_WINDOW_START,
        "window_end": FIXTURE_WINDOW_END,
        "primary_market_ids": fixture_primary_markets(),
    }
    a = build_fixture_datasets(**kwargs)
    b = build_fixture_datasets(**kwargs)
    for horizon in FORECAST_HORIZONS:
        assert [r.to_export_dict() for r in a.datasets[horizon]] == [
            r.to_export_dict() for r in b.datasets[horizon]
        ]


def test_horizons_tuple() -> None:
    assert FORECAST_HORIZONS == (30, 60, 90)


@pytest.mark.integration
def test_database_build_when_corpus_loaded(migrated_database: str) -> None:
    """@5433 integration: skip when PI8/PI9 observation corpus is not loaded."""
    from datetime import date

    from sqlalchemy import create_engine, text
    from sqlalchemy.orm import Session

    from forecasting.datasets.builder import ForecastDatasetBuilder

    engine = create_engine(migrated_database, pool_pre_ping=True)
    with engine.connect() as conn:
        count = conn.execute(
            text(
                "SELECT COUNT(*) FROM price_observation "
                "WHERE commodity_id = 'cotton' AND validation_status = 'validated'"
            )
        ).scalar_one()
    if count == 0:
        pytest.skip("No validated cotton prices on integration DB")

    with Session(engine) as session:
        result = ForecastDatasetBuilder(session).build_from_database(
            window_start=date(2023, 6, 1),
            window_end=date(2026, 6, 3),
        )
    engine.dispose()
    assert result.metadata.mode == "database"
    assert result.stats[30].row_count > 0


def test_row_export_includes_registry_when_present() -> None:
    row = ForecastDatasetRow(
        as_of_date=date(2026, 1, 1),
        commodity_id="cotton",
        horizon_days=30,
        spot_price_level=Decimal("7000"),
        target_price_level=Decimal("7100"),
        target_log_return=0.01,
        registry_id=fixture_snapshots_by_date()[FIXTURE_WINDOW_START].registry_id,
        snapshot_hash="abc",
        features={"signal_market_confidence": 0.7},
    )
    exported = row.to_export_dict()
    assert exported["registry_id"]
    assert exported["signal_market_confidence"] == 0.7
