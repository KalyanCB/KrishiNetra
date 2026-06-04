"""ForecastQualityMetric repository — PI11 Track D."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.forecast_quality import ForecastQualityMetricModel
from backend.app.persistence.repositories.base import BaseRepository


class ForecastQualityMetricRepository(BaseRepository[ForecastQualityMetricModel]):
    """Upsert forecast backtest KPI rows by natural key."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ForecastQualityMetricModel)

    def get_metric(
        self,
        *,
        commodity_id: str,
        as_of_date: date,
        registry_id: UUID,
        horizon_days: int,
        model_version: str | None,
        assessment_source: str,
    ) -> ForecastQualityMetricModel | None:
        stmt = select(ForecastQualityMetricModel).where(
            ForecastQualityMetricModel.commodity_id == commodity_id,
            ForecastQualityMetricModel.as_of_date == as_of_date,
            ForecastQualityMetricModel.registry_id == registry_id,
            ForecastQualityMetricModel.horizon_days == horizon_days,
            ForecastQualityMetricModel.assessment_source == assessment_source,
        )
        if model_version is None:
            stmt = stmt.where(ForecastQualityMetricModel.model_version.is_(None))
        else:
            stmt = stmt.where(
                ForecastQualityMetricModel.model_version == model_version
            )
        return self._session.scalars(stmt).first()

    def upsert_metric(
        self, entity: ForecastQualityMetricModel
    ) -> ForecastQualityMetricModel:
        """Insert or replace metrics for the natural assessment key."""
        existing = self.get_metric(
            commodity_id=entity.commodity_id,
            as_of_date=entity.as_of_date,
            registry_id=entity.registry_id,
            horizon_days=entity.horizon_days,
            model_version=entity.model_version,
            assessment_source=entity.assessment_source,
        )
        if existing is None:
            return self.insert(entity)
        existing.forecast_version_id = entity.forecast_version_id
        existing.sample_count = entity.sample_count
        existing.mae = entity.mae
        existing.rmse = entity.rmse
        existing.mape = entity.mape
        existing.coverage = entity.coverage
        existing.metrics_detail = entity.metrics_detail
        self._session.flush()
        return existing
