"""PI11 Track D: ForecastQualityService unit tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from tests.fixtures.forecast_quality import (
    AS_OF_DATE,
    COTTON_COMMODITY_ID,
    MODEL_VERSION,
    REGISTRY_ID,
    multi_horizon_evaluation_pairs,
    sample_evaluation_pairs,
)
from tests.fixtures.signal_quality import pi9_registry

from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
from backend.app.persistence.repositories.forecast_quality import (
    ForecastQualityMetricRepository,
)
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.services.forecast.quality.metrics import (
    build_forecast_quality_by_horizon,
    compute_interval_coverage,
    compute_mae,
    compute_mape,
    compute_rmse,
    pair_from_horizon_payload,
)
from backend.app.services.forecast.quality.service import (
    ForecastQualityService,
    render_forecast_quality_report_markdown,
)
from shared.domain.enums import Direction


def test_compute_mae_rmse_on_known_errors() -> None:
    errors = [10.0, -20.0, 5.0]
    assert compute_mae(errors=errors) == pytest.approx(11.6667, rel=1e-3)
    assert compute_rmse(errors=errors) == pytest.approx(13.2288, rel=1e-3)


def test_compute_mape_skips_near_zero_actual() -> None:
    mape = compute_mape(
        predicted=[100.0, 200.0],
        actual=[0.0, 200.0],
    )
    assert mape == pytest.approx(0.0)


def test_compute_interval_coverage() -> None:
    coverage = compute_interval_coverage(
        actual=[105.0, 180.0, 52.0],
        band_low=[95.0, 170.0, 40.0],
        band_high=[115.0, 210.0, 49.0],
    )
    assert coverage == pytest.approx(2 / 3)


def test_build_metrics_sample_pairs() -> None:
    by_horizon = build_forecast_quality_by_horizon(sample_evaluation_pairs())
    metrics = by_horizon[30]
    assert metrics.sample_count == 3
    assert metrics.mae == pytest.approx(10.6667, rel=1e-3)
    assert metrics.rmse == pytest.approx(12.961, rel=1e-3)
    assert metrics.mape == pytest.approx(8.0161, rel=1e-3)
    assert metrics.coverage == pytest.approx(2 / 3)


def test_pair_from_horizon_payload() -> None:
    pair = pair_from_horizon_payload(
        horizon_days=30,
        horizon={
            "point": 5500.0,
            "band_low": 5200.0,
            "band_high": 5800.0,
            "direction": Direction.BULLISH.value,
            "forecast_confidence": 0.8,
        },
        actual_price=5600.0,
        as_of_date="2025-12-01",
    )
    assert pair.predicted == 5500.0
    assert pair.actual == 5600.0
    assert pair.band_low == 5200.0


def test_forecast_quality_service_assess_multi_horizon() -> None:
    engine = create_engine("sqlite:///:memory:")
    with Session(engine) as session:
        service = ForecastQualityService(session)
        result = service.assess(
            multi_horizon_evaluation_pairs(),
            commodity_id=COTTON_COMMODITY_ID,
            as_of_date=AS_OF_DATE,
            registry_id=REGISTRY_ID,
            model_version=MODEL_VERSION,
        )
    assert result.sample_count_total == 3
    assert result.by_horizon[30].mae == pytest.approx(100.0)
    assert result.by_horizon[60].mae == pytest.approx(200.0)
    assert result.by_horizon[90].coverage == pytest.approx(1.0)


def test_render_report_markdown_contains_kpis() -> None:
    engine = create_engine("sqlite:///:memory:")
    with Session(engine) as session:
        result = ForecastQualityService(session).assess(
            sample_evaluation_pairs(),
            commodity_id=COTTON_COMMODITY_ID,
            as_of_date=AS_OF_DATE,
            registry_id=REGISTRY_ID,
            model_version=MODEL_VERSION,
        )
    body = render_forecast_quality_report_markdown(result=result)
    assert "Forecast Quality Report — PI11 Track D" in body
    assert "forecast_quality_metric" in body
    assert "MAE" in body


def _cleanup_forecast_quality_fixtures(session: Session) -> None:
    commodity_id = "forecast_quality_test"
    session.execute(
        text(
            "DELETE FROM forecast_quality_metric WHERE commodity_id = :cid"
        ),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM commodity_registry WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM commodity WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.commit()


@pytest.mark.integration
def test_forecast_quality_assess_and_persist(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_forecast_quality_fixtures(session)

        commodity = CommodityModel(
            commodity_id="forecast_quality_test",
            name="Forecast Quality Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()

        registry = pi9_registry()
        registry.commodity_id = "forecast_quality_test"
        CommodityRegistryRepository(session).insert_version(registry)

        service = ForecastQualityService(session)
        result, rows = service.assess_and_persist(
            multi_horizon_evaluation_pairs(),
            commodity_id="forecast_quality_test",
            as_of_date=AS_OF_DATE,
            registry_id=registry.registry_id,
            model_version=MODEL_VERSION,
        )
        session.commit()

        assert len(rows) == 3
        assert result.sample_count_total == 3

        loaded = ForecastQualityMetricRepository(session).get_metric(
            commodity_id="forecast_quality_test",
            as_of_date=AS_OF_DATE,
            registry_id=registry.registry_id,
            horizon_days=30,
            model_version=MODEL_VERSION,
            assessment_source="backtest",
        )
        assert loaded is not None
        assert loaded.sample_count == 1
        assert float(loaded.mae) == pytest.approx(100.0)

        result2, rows2 = service.assess_and_persist(
            multi_horizon_evaluation_pairs(),
            commodity_id="forecast_quality_test",
            as_of_date=AS_OF_DATE,
            registry_id=registry.registry_id,
            model_version=MODEL_VERSION,
        )
        session.commit()
        assert len(rows2) == 3
        assert rows2[0].forecast_quality_id == rows[0].forecast_quality_id

        _cleanup_forecast_quality_fixtures(session)
    engine.dispose()
