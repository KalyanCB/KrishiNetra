"""ForecastModelRegistry service — PI11 Track E."""

from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.app.persistence.models.forecast import ForecastModelRegistryModel
from backend.app.persistence.repositories.forecast import (
    ForecastModelRegistryRepository,
)
from backend.app.services.forecast.registry.types import (
    ForecastModelMetrics,
    TrainingWindow,
)


class ForecastModelRegistryService:
    """
    Register trained forecast models with version, training window, metrics,
    and feature-set identity (id + hash).
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._registry = ForecastModelRegistryRepository(session)

    def register(
        self,
        *,
        commodity_id: str,
        registry_id: UUID,
        model_version: str,
        training_window: TrainingWindow,
        metrics: ForecastModelMetrics,
        feature_set_hash: str,
        model_family: str | None = None,
        feature_set_id: UUID | None = None,
        forecast_model_registry_id: UUID | None = None,
    ) -> ForecastModelRegistryModel:
        entity = ForecastModelRegistryModel(
            forecast_model_registry_id=forecast_model_registry_id or uuid4(),
            commodity_id=commodity_id,
            registry_id=registry_id,
            model_version=model_version,
            model_family=model_family,
            horizon_days=metrics.horizon_days,
            training_window_start=training_window.start,
            training_window_end=training_window.end,
            metrics={
                "mae": metrics.mae,
                "rmse": metrics.rmse,
                "mape": metrics.mape,
            },
            feature_set_id=feature_set_id,
            feature_set_hash=feature_set_hash,
        )
        return self._registry.insert_entry(entity)

    def get(
        self, forecast_model_registry_id: UUID
    ) -> ForecastModelRegistryModel | None:
        return self._registry.get_entry(forecast_model_registry_id)

    def resolve(
        self,
        *,
        commodity_id: str,
        registry_id: UUID,
        model_version: str,
        training_window: TrainingWindow,
        feature_set_hash: str,
    ) -> ForecastModelRegistryModel | None:
        return self._registry.get_by_model_version(
            commodity_id=commodity_id,
            registry_id=registry_id,
            model_version=model_version,
            training_window_start=training_window.start,
            training_window_end=training_window.end,
            feature_set_hash=feature_set_hash,
        )
