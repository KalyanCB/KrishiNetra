"""Forecast, ForecastVersion, and feature store repositories — E-01-S06."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.forecast import (
    FeatureSetModel,
    FeatureVectorModel,
    ForecastModel,
    ForecastVersionModel,
)
from backend.app.persistence.repositories.base import (
    BaseRepository,
    ImmutableVersionRepository,
)
from backend.app.persistence.validation.forecast import (
    validate_forecast_version_horizons,
)


class ForecastRepository(BaseRepository[ForecastModel]):
    """Logical forecast identity — insert and lookup by id."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ForecastModel)


class FeatureSetRepository(BaseRepository[FeatureSetModel]):
    """Feature store metadata — insert-only."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, FeatureSetModel)

    def insert_feature_set(self, entity: FeatureSetModel) -> FeatureSetModel:
        return self.insert(entity)


class FeatureVectorRepository(BaseRepository[FeatureVectorModel]):
    """Feature vectors keyed by (feature_set_id, feature_name)."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, FeatureVectorModel)

    def insert_vector(self, entity: FeatureVectorModel) -> FeatureVectorModel:
        return self.insert(entity)


class ForecastVersionRepository(ImmutableVersionRepository[ForecastVersionModel]):
    """Insert-only forecast versions; UPDATE blocked at repository layer."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ForecastVersionModel)

    def insert_version(
        self, entity: ForecastVersionModel
    ) -> ForecastVersionModel:
        validate_forecast_version_horizons(
            horizon_30=entity.horizon_30,
            horizon_60=entity.horizon_60,
            horizon_90=entity.horizon_90,
        )
        return self.insert(entity)

    def get_version(
        self, forecast_version_id: UUID, *, as_of_date: date
    ) -> ForecastVersionModel | None:
        return self._session.get(
            self._model, (forecast_version_id, as_of_date)
        )

    def get_published(
        self,
        commodity_id: str,
        as_of_date: date,
        registry_id: UUID,
    ) -> ForecastVersionModel | None:
        stmt = (
            select(ForecastVersionModel)
            .where(
                ForecastVersionModel.commodity_id == commodity_id,
                ForecastVersionModel.as_of_date == as_of_date,
                ForecastVersionModel.registry_id == registry_id,
                ForecastVersionModel.is_published.is_(True),
            )
            .order_by(ForecastVersionModel.generated_at.desc())
        )
        return self._session.scalars(stmt).first()
