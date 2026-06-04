"""PI9 Track E: SignalQualityService unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tests.fixtures.signal_quality import (
    AS_OF_DATE,
    AS_OF_TIMESTAMP,
    COTTON_COMMODITY_ID,
    NOW_FRESH,
    NOW_STALE,
    market_and_weather_signals,
    pi9_registry,
    snapshot_for_signals,
    structured_signal_row,
)

from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.repositories.signal import (
    SignalSnapshotRepository,
    StructuredSignalRepository,
)
from backend.app.persistence.validation.signal import structured_signal_to_persisted_row
from backend.app.services.signals.quality.metrics import (
    build_signal_quality_metrics,
    classify_signal_freshness,
    compute_confidence_aggregates,
)
from backend.app.services.signals.quality.service import (
    SignalQualityService,
    _metrics_from_rows,
    compute_signal_quality_metrics,
    render_signal_quality_report_markdown,
)
from shared.domain.enums import AgentType


def test_confidence_aggregates_empty() -> None:
    agg = compute_confidence_aggregates(agent_confidences={})
    assert agg.count == 0
    assert agg.mean_confidence is None


def test_confidence_aggregates_multiple_agents() -> None:
    agg = compute_confidence_aggregates(
        agent_confidences={
            AgentType.MARKET.value: Decimal("0.80"),
            AgentType.WEATHER.value: Decimal("0.60"),
        }
    )
    assert agg.count == 2
    assert agg.min_confidence == Decimal("0.60")
    assert agg.max_confidence == Decimal("0.80")
    assert agg.mean_confidence == Decimal("0.7000")


def test_classify_signal_freshness_missing_without_rows() -> None:
    assert (
        classify_signal_freshness(signal_lag_hours=None, has_signals=False) == "missing"
    )


def test_classify_signal_freshness_fresh_when_recent() -> None:
    assert (
        classify_signal_freshness(signal_lag_hours=2.0, has_signals=True) == "fresh"
    )


def test_classify_signal_freshness_stale_when_lag_high() -> None:
    assert (
        classify_signal_freshness(signal_lag_hours=72.0, has_signals=True) == "stale"
    )


def test_build_metrics_reports_missing_required_agents() -> None:
    registry = pi9_registry()
    metrics = build_signal_quality_metrics(
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=AS_OF_DATE,
        registry_id=registry.registry_id,
        agent_confidences={AgentType.MARKET.value: Decimal("0.70")},
        required_agents=list(registry.required_agents),
        optional_agents=registry.optional_agents,
        latest_as_of_timestamp=AS_OF_TIMESTAMP,
        snapshot_signal_count=1,
        snapshot_present=True,
        snapshot_hash="abc123",
        now=NOW_FRESH,
    )
    assert metrics.signal_count == 1
    assert AgentType.FUTURES.value in metrics.signals_missing
    assert metrics.required_coverage_ratio == 0.5
    assert metrics.coverage_ratio == pytest.approx(1 / 4)
    assert metrics.freshness == "fresh"
    assert metrics.confidence.mean_confidence == Decimal("0.70")


def test_build_metrics_market_and_weather_with_snapshot() -> None:
    registry = pi9_registry()
    market, weather = market_and_weather_signals(registry.registry_id)
    snapshot = snapshot_for_signals([market, weather], registry_id=registry.registry_id)
    metrics = _metrics_from_rows(
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=AS_OF_DATE,
        registry=registry,
        signals=[market, weather],
        snapshot=snapshot,
        now=NOW_FRESH,
    )
    assert metrics.signal_count == 2
    assert metrics.snapshot_signal_count == 2
    assert metrics.snapshot_aligned is True
    assert metrics.confidence.mean_confidence == Decimal("0.6150")
    assert AgentType.WEATHER.value in metrics.agents_present_list
    assert AgentType.FUTURES.value in metrics.signals_missing


def test_compute_metrics_empty_session() -> None:
    registry = pi9_registry()
    session = MagicMock()
    signal_repo = MagicMock()
    signal_repo.list_by_commodity_date.return_value = []
    snapshot_repo = MagicMock()
    snapshot_repo.get_snapshot.return_value = None

    with patch(
        "backend.app.services.signals.quality.service.StructuredSignalRepository",
        return_value=signal_repo,
    ), patch(
        "backend.app.services.signals.quality.service.SignalSnapshotRepository",
        return_value=snapshot_repo,
    ):
        metrics = compute_signal_quality_metrics(
            session,
            commodity_id=COTTON_COMMODITY_ID,
            as_of_date=AS_OF_DATE,
            registry=registry,
            now=NOW_STALE,
        )

    assert metrics.signal_count == 0
    assert metrics.freshness == "missing"
    assert metrics.signals_missing == tuple(registry.required_agents)


@patch("backend.app.services.signals.quality.service.RegistryService")
def test_signal_quality_service_assess(mock_registry_cls: MagicMock) -> None:
    registry = pi9_registry()
    mock_registry_cls.return_value.get_active_config.return_value = registry
    market = structured_signal_row(AgentType.MARKET, registry_id=registry.registry_id)

    session = MagicMock()
    signal_repo = MagicMock()
    signal_repo.list_by_commodity_date.return_value = [market]
    snapshot_repo = MagicMock()
    snapshot_repo.get_snapshot.return_value = None

    with patch(
        "backend.app.services.signals.quality.service.StructuredSignalRepository",
        return_value=signal_repo,
    ), patch(
        "backend.app.services.signals.quality.service.SignalSnapshotRepository",
        return_value=snapshot_repo,
    ):
        result = SignalQualityService(session).assess(
            commodity_id=COTTON_COMMODITY_ID,
            as_of_date=AS_OF_DATE,
            now=NOW_FRESH,
        )

    assert result.metrics.signal_count == 1
    assert result.registry_id == registry.registry_id


def test_render_report_markdown_contains_core_metrics() -> None:
    registry = pi9_registry()
    market, weather = market_and_weather_signals(registry.registry_id)
    metrics = _metrics_from_rows(
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=AS_OF_DATE,
        registry=registry,
        signals=[market, weather],
        snapshot=None,
        now=NOW_FRESH,
    )
    from backend.app.services.signals.quality.service import SignalQualityResult

    body = render_signal_quality_report_markdown(
        result=SignalQualityResult(
            metrics=metrics,
            commodity_id=COTTON_COMMODITY_ID,
            as_of_date=AS_OF_DATE,
            registry_id=registry.registry_id,
        )
    )
    assert "Signal Quality Report — PI9 Track E" in body
    assert "coverage_ratio" in body
    assert "0.615" in body


def _cleanup_signal_quality_fixtures(session: Session) -> None:
    from sqlalchemy import text

    commodity_id = "signal_quality_test"
    session.execute(
        text(f"DELETE FROM signal_snapshot WHERE commodity_id = '{commodity_id}'")
    )
    session.execute(
        text(f"DELETE FROM structured_signal WHERE commodity_id = '{commodity_id}'")
    )
    session.execute(
        text(f"DELETE FROM commodity_registry WHERE commodity_id = '{commodity_id}'")
    )
    session.execute(text(f"DELETE FROM commodity WHERE commodity_id = '{commodity_id}'"))
    session.commit()


@pytest.mark.integration
def test_signal_quality_assess_persisted_rows(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_signal_quality_fixtures(session)

        commodity = CommodityModel(
            commodity_id="signal_quality_test",
            name="Signal Quality Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()

        registry = pi9_registry()
        registry.commodity_id = "signal_quality_test"
        CommodityRegistryRepository(session).insert_version(registry)

        market, weather = market_and_weather_signals(registry.registry_id)
        for row in (market, weather):
            row.commodity_id = "signal_quality_test"
            StructuredSignalRepository(session).insert_signal(row)

        snapshot = snapshot_for_signals(
            [market, weather],
            registry_id=registry.registry_id,
        )
        snapshot.commodity_id = "signal_quality_test"
        payloads = [
            structured_signal_to_persisted_row(row) for row in (market, weather)
        ]
        SignalSnapshotRepository(session).insert_snapshot(
            snapshot, signal_payloads=payloads
        )
        session.commit()

        result = SignalQualityService(session).assess(
            commodity_id="signal_quality_test",
            as_of_date=AS_OF_DATE,
            registry=registry,
            now=datetime(2026, 6, 4, 15, 0, tzinfo=UTC),
        )

        assert result.metrics.signal_count == 2
        assert result.metrics.snapshot_aligned is True
        assert result.metrics.confidence.count == 2

        _cleanup_signal_quality_fixtures(session)
    engine.dispose()
