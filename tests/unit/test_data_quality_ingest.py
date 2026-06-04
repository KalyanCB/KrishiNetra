"""PI6 Track E: data_quality_snapshot ingest wiring tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.repositories.quality import DataQualitySnapshotRepository
from backend.app.persistence.seeds.runner import SeedRunner
from backend.app.services.ingest.agmarknet.backfill import BackfillWindow
from backend.app.services.ingest.agmarknet.pipeline import AgmarknetIngestPipeline
from backend.app.services.quality.metrics import (
    AgmarknetQualityMetrics,
    WeatherQualityMetrics,
    classify_source_health,
    compute_overall_quality_score,
    coverage_ratio,
)
from backend.app.services.quality.snapshot_service import (
    DataQualitySnapshotService,
    _combined_overall_score,
    compute_agmarknet_metrics,
)
from backend.app.services.registry.service import RegistryService

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "agmarknet"
    / "ogd_telangana_sample.json"
)


def test_coverage_ratio_caps_at_one() -> None:
    assert coverage_ratio(5, 4) == 1.0
    assert coverage_ratio(0, 4) == 0.0


def test_classify_source_health_missing_without_data() -> None:
    assert (
        classify_source_health(
            coverage_ratio=0.0,
            completeness_ratio=0.0,
            lag_hours_value=None,
            has_data=False,
        )
        == "missing"
    )


def test_classify_source_health_fresh_when_healthy() -> None:
    assert (
        classify_source_health(
            coverage_ratio=1.0,
            completeness_ratio=0.9,
            lag_hours_value=2.0,
            has_data=True,
        )
        == "fresh"
    )


def test_combined_score_ignores_empty_weather_tier() -> None:
    ag = AgmarknetQualityMetrics(
        markets_expected=4,
        markets_reporting=2,
        coverage_ratio=0.5,
        window_days=30,
        days_with_data=29,
        completeness_ratio=29 / 30,
        latest_as_of_date=date(2026, 6, 4),
        latest_observed_at=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        agmarknet_lag_hours=2.0,
        anomaly_count=0,
    )
    empty_weather = WeatherQualityMetrics(
        regions_expected=5,
        regions_reporting=0,
        coverage_ratio=0.0,
        window_days=30,
        days_with_data=0,
        completeness_ratio=0.0,
        latest_as_of_date=None,
        latest_observed_at=None,
        weather_lag_hours=None,
        anomaly_count=0,
    )
    ag_only = _combined_overall_score(ag_metrics=ag, weather_metrics=None)
    with_empty = _combined_overall_score(
        ag_metrics=ag, weather_metrics=empty_weather
    )
    assert ag_only == with_empty


def test_compute_overall_quality_score_in_unit_interval() -> None:
    score = compute_overall_quality_score(
        coverage_ratio=0.75,
        completeness_ratio=0.5,
        lag_hours_value=12.0,
        anomaly_count=2,
        row_count=100,
    )
    assert Decimal("0") <= score <= Decimal("1")


def test_agmarknet_metrics_empty_session() -> None:
    session = MagicMock()
    session.scalar.return_value = None
    metrics = compute_agmarknet_metrics(
        session,
        window_start=date(2026, 6, 1),
        window_end=date(2026, 6, 30),
        expected_market_ids=("mkt_a", "mkt_b"),
        now=datetime(2026, 6, 30, 12, 0, tzinfo=UTC),
    )
    assert metrics.markets_reporting == 0
    assert metrics.coverage_ratio == 0.0
    assert metrics.anomaly_count == 0


def _delete_cotton_quality_rows(session: Session) -> None:
    from sqlalchemy import text

    from backend.app.spike.agmarknet.population import (
        delete_cotton_agmarknet_observations,
    )

    delete_cotton_agmarknet_observations(session)
    session.execute(
        text("DELETE FROM data_quality_snapshot WHERE commodity_id = 'cotton'")
    )


@pytest.mark.integration
def test_quality_snapshot_after_agmarknet_fixture(migrated_database: str) -> None:

    engine = create_engine(migrated_database, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            _delete_cotton_quality_rows(session)
            session.commit()

        with Session(engine) as session:
            SeedRunner(session).apply("cotton")
            session.flush()
            registry = RegistryService(session).get_active_config("cotton")

            pipeline = AgmarknetIngestPipeline(session)
            pipeline.ingest_from_fixture(FIXTURE_PATH)
            session.commit()

            snapshot = session.scalars(
                select(DataQualitySnapshotModel)
                .where(
                    DataQualitySnapshotModel.commodity_id == "cotton",
                    DataQualitySnapshotModel.registry_id == registry.registry_id,
                )
                .order_by(DataQualitySnapshotModel.as_of_date.desc())
            ).first()

        assert snapshot is not None
        assert snapshot.registry_id == registry.registry_id
        assert snapshot.agmarknet_lag_hours is not None
        detail = snapshot.source_health.get("agmarknet_detail", {})
        from backend.app.services.ingest.agmarknet.expected_markets import (
            load_expected_market_ids,
        )

        assert detail.get("markets_expected") == len(load_expected_market_ids())
        assert detail.get("markets_reporting", 0) >= 1
        assert detail.get("anomaly_count", 0) >= 0
        assert snapshot.source_health.get("agmarknet") in {
            "fresh",
            "stale",
            "missing",
        }
    finally:
        with Session(engine) as session:
            _delete_cotton_quality_rows(session)
            session.commit()
        engine.dispose()


@pytest.mark.integration
def test_quality_snapshot_upsert_refreshes_metrics(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    fixed_now = datetime(2026, 6, 4, 18, 0, tzinfo=UTC)
    try:
        with Session(engine) as session:
            _delete_cotton_quality_rows(session)
            session.commit()

        with Session(engine) as session:
            SeedRunner(session).apply("cotton")
            session.flush()
            service = DataQualitySnapshotService(session)
            first = service.record_after_agmarknet_ingest(
                as_of_date=date(2026, 6, 4),
                now=fixed_now,
            )
            session.commit()
            second = service.record_after_agmarknet_ingest(
                as_of_date=date(2026, 6, 4),
                now=fixed_now,
            )
            session.commit()

            rows = session.scalars(
                select(DataQualitySnapshotModel).where(
                    DataQualitySnapshotModel.commodity_id == "cotton",
                    DataQualitySnapshotModel.as_of_date == date(2026, 6, 4),
                )
            ).all()

        assert first.quality_snapshot_id == second.quality_snapshot_id
        assert len(rows) == 1
    finally:
        with Session(engine) as session:
            _delete_cotton_quality_rows(session)
            session.commit()
        engine.dispose()


@pytest.mark.integration
def test_backfill_writes_quality_snapshot(migrated_database: str) -> None:
    from backend.app.services.ingest.agmarknet.backfill import (
        AgmarknetBackfillPipeline,
        FixtureReplayOgdClient,
    )

    window = BackfillWindow(start=date(2022, 3, 26), end=date(2022, 3, 26))
    engine = create_engine(migrated_database, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            _delete_cotton_quality_rows(session)
            session.commit()

        with Session(engine) as session:
            client = FixtureReplayOgdClient(FIXTURE_PATH)
            AgmarknetBackfillPipeline(session, ogd_client=client).run(
                window, dry_run=False
            )
            session.commit()
            registry = RegistryService(session).get_active_config("cotton")
            snapshot = DataQualitySnapshotRepository(session).get_by_commodity_date(
                "cotton",
                window.end,
                registry_id=registry.registry_id,
            )

        assert snapshot is not None
        detail = snapshot.source_health["agmarknet_detail"]
        assert detail["window_days"] == window.days
    finally:
        with Session(engine) as session:
            _delete_cotton_quality_rows(session)
            session.commit()
        engine.dispose()
