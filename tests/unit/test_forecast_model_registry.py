"""PI11 Track E: ForecastModelRegistry persistence and service tests."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from backend.app.persistence.models.forecast import ForecastModelRegistryModel
from backend.app.persistence.repositories.forecast import (
    ForecastModelRegistryRepository,
)
from backend.app.persistence.validation.forecast_model_registry import (
    ForecastModelRegistryValidationError,
    validate_feature_set_hash,
    validate_metrics,
    validate_training_window,
)
from backend.app.services.forecast.registry.service import ForecastModelRegistryService
from backend.app.services.forecast.registry.types import (
    ForecastModelMetrics,
    TrainingWindow,
)
from shared.persistence.contracts import ImmutableVersionUpdateError

_FEATURE_HASH = "a" * 64


def test_validate_training_window_rejects_inverted_range() -> None:
    with pytest.raises(ForecastModelRegistryValidationError, match="training_window"):
        validate_training_window(start=date(2026, 6, 4), end=date(2026, 1, 1))


def test_validate_feature_set_hash_length() -> None:
    with pytest.raises(ForecastModelRegistryValidationError, match="64 hex"):
        validate_feature_set_hash("short")


def test_validate_metrics_requires_mae_rmse_mape() -> None:
    with pytest.raises(ForecastModelRegistryValidationError, match="mae"):
        validate_metrics({"rmse": 1.0, "mape": 2.0})
    normalized = validate_metrics({"mae": 10.0, "rmse": 12.0, "mape": 5.5})
    assert normalized == {"mae": 10.0, "rmse": 12.0, "mape": 5.5}


def test_forecast_model_metrics_as_dict() -> None:
    metrics = ForecastModelMetrics(mae=1.0, rmse=2.0, mape=3.0, horizon_days=30)
    assert metrics.as_dict()["horizon_days"] == 30


def test_registry_repository_update_blocked() -> None:
    session = MagicMock(spec=Session)
    repo = ForecastModelRegistryRepository(session)
    with pytest.raises(ImmutableVersionUpdateError, match="UPDATE blocked"):
        repo.update(ForecastModelRegistryModel())  # type: ignore[call-arg]


def test_registry_repository_insert_entry_validates() -> None:
    session = MagicMock(spec=Session)
    repo = ForecastModelRegistryRepository(session)
    entity = ForecastModelRegistryModel(
        forecast_model_registry_id=uuid4(),
        commodity_id="cotton_test",
        registry_id=uuid4(),
        model_version="rf-v1.0.0-seed42",
        horizon_days=30,
        training_window_start=date(2026, 6, 4),
        training_window_end=date(2026, 1, 1),
        metrics={"mae": 1.0, "rmse": 2.0, "mape": 3.0},
        feature_set_hash=_FEATURE_HASH,
    )
    with pytest.raises(ForecastModelRegistryValidationError):
        repo.insert_entry(entity)


def test_register_persists_entry_via_service() -> None:
    session = MagicMock(spec=Session)
    registry_id = uuid4()
    feature_set_id = uuid4()
    service = ForecastModelRegistryService(session)
    entry = service.register(
        commodity_id="cotton_test",
        registry_id=registry_id,
        model_version="linear-v1.0.0-seed42",
        model_family="linear_regression",
        training_window=TrainingWindow(start=date(2025, 1, 1), end=date(2026, 5, 31)),
        metrics=ForecastModelMetrics(mae=450.0, rmse=520.0, mape=4.2),
        feature_set_id=feature_set_id,
        feature_set_hash=_FEATURE_HASH,
    )
    assert entry.model_version == "linear-v1.0.0-seed42"
    assert entry.horizon_days == 30
    assert entry.metrics["mae"] == 450.0
    assert entry.feature_set_id == feature_set_id
    assert entry.feature_set_hash == _FEATURE_HASH
    session.add.assert_called_once()


@pytest.mark.integration
def test_forecast_model_registry_integration(
    migrated_database: str,
) -> None:
    """Register and resolve entry when DATABASE_URL is set."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from tests.unit.test_forecast_feature_store import _decision_rules

    from backend.app.persistence.models.forecast import FeatureSetModel
    from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
    from backend.app.persistence.models.registry import CommodityRegistryModel
    from backend.app.persistence.repositories.registry import (
        CommodityRegistryRepository,
    )

    engine = create_engine(migrated_database, pool_pre_ping=True)
    session_factory = sessionmaker(bind=engine)
    commodity_id = f"registry_pi11_{uuid4().hex[:8]}"
    with session_factory() as session:
        commodity = CommodityModel(
            commodity_id=commodity_id,
            name="Registry PI11",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()
        registry = CommodityRegistryModel(
            registry_id=uuid4(),
            commodity_id=commodity_id,
            version="1.0.0",
            effective_from=date(2026, 1, 1),
            is_active=True,
            required_agents=["Market"],
            decision_rules=_decision_rules(),
        )
        CommodityRegistryRepository(session).insert_version(registry)
        feature_set = FeatureSetModel(
            feature_set_id=uuid4(),
            commodity_id=commodity_id,
            as_of_date=date(2026, 6, 4),
            registry_id=registry.registry_id,
            feature_hash=_FEATURE_HASH,
        )
        session.add(feature_set)
        session.commit()

        service = ForecastModelRegistryService(session)
        window = TrainingWindow(start=date(2025, 6, 1), end=date(2026, 5, 31))
        metrics = ForecastModelMetrics(mae=100.0, rmse=110.0, mape=2.5)
        registered = service.register(
            commodity_id=commodity_id,
            registry_id=registry.registry_id,
            model_version="naive-v1.0.0",
            model_family="naive_persistence",
            training_window=window,
            metrics=metrics,
            feature_set_id=feature_set.feature_set_id,
            feature_set_hash=_FEATURE_HASH,
        )
        session.commit()
        resolved = service.resolve(
            commodity_id=commodity_id,
            registry_id=registry.registry_id,
            model_version="naive-v1.0.0",
            training_window=window,
            feature_set_hash=_FEATURE_HASH,
        )
        assert resolved is not None
        assert (
            resolved.forecast_model_registry_id
            == registered.forecast_model_registry_id
        )
    engine.dispose()
