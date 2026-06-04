"""PI11 synthesis — wire Track A baseline_metrics.json into D/E services."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from tests.fixtures.forecast_quality import COTTON_COMMODITY_ID
from tests.fixtures.signal_quality import pi9_registry

from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
from backend.app.persistence.repositories.forecast import (
    ForecastModelRegistryRepository,
)
from backend.app.persistence.repositories.forecast_quality import (
    ForecastQualityMetricRepository,
)
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.services.forecast.baseline_handoff import (
    BASELINE_ASSESSMENT_SOURCE,
    BaselineHandoffService,
    feature_set_hash_for_training,
    load_baseline_metrics,
    model_version_for_baseline,
    quality_result_from_baseline_row,
    training_window_for_dataset,
)
from forecasting.datasets.fixtures import FIXTURE_REGISTRY_ID
from forecasting.datasets.training import load_fixture_training_dataset


def test_load_baseline_metrics_matches_disk_json() -> None:
    rows = load_baseline_metrics()
    assert len(rows) == 3
    names = {row.model_name for row in rows}
    assert names == {"naive_persistence", "linear_regression", "random_forest"}
    linear = next(r for r in rows if r.model_name == "linear_regression")
    assert linear.mae == 0.0
    assert linear.mape == 0.0
    assert linear.n_samples == 60


def test_quality_result_from_baseline_row() -> None:
    row = load_baseline_metrics()[0]
    result = quality_result_from_baseline_row(
        row,
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=date(2026, 1, 16),
        registry_id=FIXTURE_REGISTRY_ID,
    )
    assert result.assessment_source == BASELINE_ASSESSMENT_SOURCE
    assert result.by_horizon[30].mae == pytest.approx(row.mae)
    assert result.model_version == model_version_for_baseline(
        row.model_name, mode=row.mode
    )


def test_feature_set_hash_stable_for_fixture_training() -> None:
    dataset = load_fixture_training_dataset(horizon_days=30)
    h1 = feature_set_hash_for_training(dataset)
    h2 = feature_set_hash_for_training(load_fixture_training_dataset(horizon_days=30))
    assert h1 == h2
    assert len(h1) == 64


def test_training_window_matches_fixture_dates() -> None:
    dataset = load_fixture_training_dataset(horizon_days=30)
    window = training_window_for_dataset(dataset)
    assert window.start == min(dataset.as_of_dates)
    assert window.end == max(dataset.as_of_dates)


def test_baseline_handoff_register_via_mock_session() -> None:
    session = MagicMock(spec=Session)
    service = BaselineHandoffService(session)
    registered, quality_rows = service.sync_from_metrics_json(
        commodity_id="cotton_test",
        registry_id=uuid4(),
        as_of_date=date(2026, 1, 16),
    )
    assert len(registered) == 3
    assert len(quality_rows) == 3
    assert session.add.call_count >= 3


def _cleanup_handoff_fixtures(session: Session, commodity_id: str) -> None:
    session.execute(
        text(
            "DELETE FROM forecast_quality_metric WHERE commodity_id = :cid"
        ),
        {"cid": commodity_id},
    )
    session.execute(
        text(
            "DELETE FROM forecast_model_registry WHERE commodity_id = :cid"
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
def test_baseline_handoff_integration(migrated_database: str) -> None:
    metrics_path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "forecast_models"
        / "baseline_metrics.json"
    )
    engine = create_engine(migrated_database, pool_pre_ping=True)
    commodity_id = f"baseline_handoff_{uuid4().hex[:8]}"
    with Session(engine) as session:
        _cleanup_handoff_fixtures(session, commodity_id)

        commodity = CommodityModel(
            commodity_id=commodity_id,
            name="Baseline Handoff",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()

        registry = pi9_registry()
        registry.commodity_id = commodity_id
        CommodityRegistryRepository(session).insert_version(registry)

        registered, quality_rows = BaselineHandoffService(
            session
        ).sync_from_metrics_json(
            metrics_path=metrics_path,
            commodity_id=commodity_id,
            registry_id=registry.registry_id,
            as_of_date=date(2026, 1, 16),
        )
        session.commit()

        assert len(registered) == 3
        assert len(quality_rows) == 3

        repo = ForecastModelRegistryRepository(session)
        naive = repo.get_by_model_version(
            commodity_id=commodity_id,
            registry_id=registry.registry_id,
            model_version=model_version_for_baseline("naive_persistence", mode="fixture"),
            training_window_start=training_window_for_dataset(
                load_fixture_training_dataset()
            ).start,
            training_window_end=training_window_for_dataset(
                load_fixture_training_dataset()
            ).end,
            feature_set_hash=feature_set_hash_for_training(
                load_fixture_training_dataset()
            ),
        )
        assert naive is not None
        assert naive.metrics["mae"] == pytest.approx(450.0)

        quality = ForecastQualityMetricRepository(session).get_metric(
            commodity_id=commodity_id,
            as_of_date=date(2026, 1, 16),
            registry_id=registry.registry_id,
            horizon_days=30,
            model_version=model_version_for_baseline(
                "random_forest", mode="fixture"
            ),
            assessment_source=BASELINE_ASSESSMENT_SOURCE,
        )
        assert quality is not None
        assert float(quality.mae) == pytest.approx(164.3, rel=1e-3)

        _cleanup_handoff_fixtures(session, commodity_id)
    engine.dispose()


def test_baseline_metrics_json_roundtrip_with_train_script(tmp_path: Path) -> None:
    dataset = load_fixture_training_dataset(horizon_days=30)
    from forecasting.models.pipeline import evaluate_all_baselines, export_metrics_json

    results = evaluate_all_baselines(dataset, output_dir=tmp_path, save_models=False)
    path = export_metrics_json(results, tmp_path / "metrics.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    loaded = load_baseline_metrics(path)
    assert len(loaded) == len(payload)
