"""PI6 Track B: Agmarknet historical backfill unit tests."""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.app.services.ingest.agmarknet.backfill import (
    AgmarknetBackfillPipeline,
    BackfillWindow,
    FixtureReplayOgdClient,
    backfill_window_start,
    compute_backfill_stats,
    default_backfill_window,
    find_missing_periods,
    format_ogd_arrival_date,
    iter_backfill_dates,
    render_backfill_report_markdown,
)
from backend.app.services.ingest.agmarknet.expected_markets import (
    TELANGANA_PRIMARY_MARKET_IDS,
    load_backfill_ogd_states,
    load_expected_market_ids,
    load_telangana_primary_market_ids,
)

TELANGANA_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "agmarknet"
    / "ogd_telangana_sample.json"
)
BELT_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "agmarknet"
    / "ogd_cotton_belt_sample.json"
)


def test_load_telangana_primary_market_ids_returns_four_mandis() -> None:
    ids = load_telangana_primary_market_ids()
    assert ids == TELANGANA_PRIMARY_MARKET_IDS
    assert len(ids) == 4


def test_load_expected_market_ids_returns_twenty_seven_mandis() -> None:
    ids = load_expected_market_ids()
    assert len(ids) == 27


def test_load_backfill_ogd_states_covers_five_states() -> None:
    states = load_backfill_ogd_states()
    assert len(states) == 5
    assert "Telangana" in states
    assert "Maharashtra" in states


def test_load_expected_market_ids_returns_cotton_belt_mandis() -> None:
    ids = load_expected_market_ids()
    assert len(ids) >= 20
    assert "mkt_tg_khammam_apmc" in ids
    assert "mkt_tg_warangal" in ids
    assert "mkt_mh_amravati" in ids
    assert "mkt_gj_rajkot" in ids


def test_format_ogd_arrival_date() -> None:
    assert format_ogd_arrival_date(date(2022, 3, 26)) == "26/03/2022"


def test_default_backfill_window_36_months() -> None:
    window = default_backfill_window(months=36)
    assert window.start <= window.end
    assert window.days >= 28 * 24


def test_iter_backfill_dates_deterministic() -> None:
    window = BackfillWindow(start=date(2026, 6, 1), end=date(2026, 6, 3))
    assert iter_backfill_dates(window) == [
        date(2026, 6, 1),
        date(2026, 6, 2),
        date(2026, 6, 3),
    ]


def test_fixture_replay_client_stamps_arrival_date() -> None:
    client = FixtureReplayOgdClient(TELANGANA_FIXTURE_PATH)
    rows = client.fetch_all(filters={"arrival_date": "01/06/2026"})
    assert rows
    assert all(r["arrival_date"] == "01/06/2026" for r in rows)


def test_fixture_replay_client_filters_by_state() -> None:
    client = FixtureReplayOgdClient(TELANGANA_FIXTURE_PATH)
    tg = client.fetch_all(
        filters={"state": "Telangana", "arrival_date": "01/06/2026"}
    )
    mh = client.fetch_all(
        filters={"state": "Maharashtra", "arrival_date": "01/06/2026"}
    )
    assert len(tg) == 4
    assert mh == []


def test_belt_fixture_replay_filters_multi_state() -> None:
    client = FixtureReplayOgdClient(BELT_FIXTURE_PATH)
    tg = client.fetch_all(
        filters={"state": "Telangana", "arrival_date": "01/06/2026"}
    )
    mh = client.fetch_all(
        filters={"state": "Maharashtra", "arrival_date": "01/06/2026"}
    )
    gj = client.fetch_all(
        filters={"state": "Gujarat", "arrival_date": "01/06/2026"}
    )
    assert len(tg) == 6
    assert len(mh) == 5
    assert len(gj) == 3


def test_belt_fixture_resolves_at_least_twelve_markets() -> None:
    from backend.app.services.ingest.agmarknet.mapper import AgmarknetMapper
    from backend.app.services.ingest.agmarknet.market_lookup import (
        load_market_lookup_from_seed,
    )
    from backend.app.services.ingest.agmarknet.parser import parse_ogd_response

    client = FixtureReplayOgdClient(BELT_FIXTURE_PATH)
    raw = client.fetch_all(filters={"arrival_date": "04/06/2026"})
    records = parse_ogd_response({"records": raw})
    mapper = AgmarknetMapper(load_market_lookup_from_seed())
    market_ids: set[str] = set()
    for record in records:
        prices, _ = mapper.map_record(record)
        for price in prices:
            market_ids.add(price.market_id)
    assert len(market_ids) >= 12


def test_find_missing_periods_detects_gap() -> None:
    window = BackfillWindow(start=date(2026, 6, 1), end=date(2026, 6, 3))
    markets = ("mkt_a",)
    dates_by_market = {"mkt_a": {date(2026, 6, 1), date(2026, 6, 3)}}
    gaps = find_missing_periods(
        window, market_ids=markets, dates_by_market=dates_by_market
    )
    assert len(gaps) == 1
    assert gaps[0].start == date(2026, 6, 2)
    assert gaps[0].end == date(2026, 6, 2)
    assert gaps[0].days == 1


def test_backfill_pipeline_fixture_dry_run_three_days() -> None:
    session = MagicMock()
    session.execute.return_value.all.return_value = []

    client = FixtureReplayOgdClient(BELT_FIXTURE_PATH)
    pipeline = AgmarknetBackfillPipeline(
        session,
        ogd_client=client,
        seed_cotton=False,
        write_quality_snapshot=False,
    )
    window = BackfillWindow(start=date(2026, 6, 1), end=date(2026, 6, 3))
    result = pipeline.run(window, dry_run=True)

    states = load_backfill_ogd_states()
    expected_rows = sum(
        len(
            client.fetch_all(
                filters={
                    "state": state,
                    "arrival_date": format_ogd_arrival_date(day),
                }
            )
        )
        for day in iter_backfill_dates(window)
        for state in states
    )

    assert result.days_fetched == 3 * len(states)
    assert result.dry_run is True
    assert result.ogd_rows_fetched == expected_rows
    session.rollback.assert_called()


def test_render_backfill_report_includes_markets() -> None:
    window = BackfillWindow(start=date(2023, 6, 1), end=date(2026, 6, 3))
    from backend.app.services.ingest.agmarknet.backfill import (
        AgmarknetBackfillStats,
        MarketDateCoverage,
    )

    stats = AgmarknetBackfillStats(
        window=window,
        expected_market_ids=load_expected_market_ids(),
        price_row_count=10,
        arrival_row_count=2,
        total_row_count=12,
        markets_with_data=2,
        market_coverage=(
            MarketDateCoverage(
                "mkt_tg_khammam_apmc", 5, date(2023, 6, 1), date(2023, 6, 5)
            ),
        ),
        distinct_as_of_dates=5,
        min_as_of=date(2023, 6, 1),
        max_as_of=date(2023, 6, 5),
    )
    md = render_backfill_report_markdown(result=None, stats=stats, fixture_mode=True)
    assert "PI6 Track B" in md
    assert "mkt_tg_khammam_apmc" in md


def test_backfill_window_start_matches_nasa_pattern() -> None:
    end = date(2026, 6, 3)
    start = backfill_window_start(end, months=36)
    assert start == date(2023, 6, 1)


@pytest.mark.integration
def test_backfill_fixture_integration(migrated_database: str) -> None:
    """Optional: short fixture backfill when DATABASE_URL + migrations available."""
    if os.environ.get("KRISHI_PRESERVE_INTEGRATION_CORPUS"):
        pytest.skip("Preserves @5433 observation corpus (PI10 merge gate)")
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import Session
    from tests.integration.test_cotton_registry import _cleanup_cotton

    from backend.app.persistence.models.observation import PriceObservationModel
    from backend.app.spike.agmarknet.population import (
        delete_cotton_agmarknet_observations,
    )

    window = BackfillWindow(start=date(2022, 3, 26), end=date(2022, 3, 26))
    engine = create_engine(migrated_database, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            _cleanup_cotton(session)
            delete_cotton_agmarknet_observations(session)
            session.commit()

        with Session(engine) as session:
            client = FixtureReplayOgdClient(BELT_FIXTURE_PATH)
            pipeline = AgmarknetBackfillPipeline(session, ogd_client=client)
            first = pipeline.run(window, dry_run=False)
            session.commit()
            second = pipeline.run(window, dry_run=False)
            session.commit()
            stats = compute_backfill_stats(session, window)
            count = session.scalar(
                select(func.count())
                .select_from(PriceObservationModel)
                .where(
                    PriceObservationModel.source == "agmarknet",
                    PriceObservationModel.commodity_id == "cotton",
                )
            )

        assert first.total_inserted > 0
        assert second.total_inserted == 0
        assert stats.markets_with_data >= 1
        assert count == first.prices_inserted
    finally:
        with Session(engine) as session:
            delete_cotton_agmarknet_observations(session)
            _cleanup_cotton(session)
            session.commit()
        engine.dispose()


def test_partition_migration_month_count() -> None:
    import importlib.util

    migration_path = (
        Path(__file__).resolve().parents[2]
        / "backend/app/persistence/migrations/versions"
        / "0010_observation_partitions_backfill.py"
    )
    spec = importlib.util.spec_from_file_location("migration_0010", migration_path)
    assert spec and spec.loader
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    months = migration._month_starts(
        migration._PARTITION_RANGE_START,
        migration._PARTITION_RANGE_END,
    )
    suffixes = [s for _, _, s in months if s not in migration._SKIP_SUFFIXES]
    assert "2023_06" in suffixes
    assert "2026_12" in suffixes
    assert "2026_06" not in suffixes
    assert len(suffixes) == 42
