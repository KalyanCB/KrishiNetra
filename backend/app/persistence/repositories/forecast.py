"""Forecast, ForecastVersion, and feature store repositories — E-01-S06."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.forecast import (
    FeatureSetModel,
    FeatureVectorModel,
    ForecastFeatureSnapshotModel,
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
from backend.app.persistence.validation.forecast_features import (
    compute_feature_hash,
    validate_trace_id,
)
from shared.persistence.contracts import block_immutable_update


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


class ForecastFeatureSnapshotRepository(BaseRepository[ForecastFeatureSnapshotModel]):
    """PI10 Track C — append-only ForecastFeatureSnapshot on feature_set."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ForecastFeatureSnapshotModel)

    def get_snapshot(
        self,
        commodity_id: str,
        as_of_date: date,
        registry_id: UUID,
    ) -> ForecastFeatureSnapshotModel | None:
        stmt = (
            select(ForecastFeatureSnapshotModel)
            .where(
                ForecastFeatureSnapshotModel.commodity_id == commodity_id,
                ForecastFeatureSnapshotModel.as_of_date == as_of_date,
                ForecastFeatureSnapshotModel.registry_id == registry_id,
            )
            .order_by(ForecastFeatureSnapshotModel.created_at.desc())
        )
        return self._session.scalars(stmt).first()

    def get_snapshot_by_trace_id(
        self, trace_id: UUID
    ) -> ForecastFeatureSnapshotModel | None:
        stmt = select(ForecastFeatureSnapshotModel).where(
            ForecastFeatureSnapshotModel.trace_id == trace_id
        )
        return self._session.scalars(stmt).first()

    def insert_snapshot(
        self,
        entity: ForecastFeatureSnapshotModel,
        *,
        feature_values: dict[str, object],
        feature_lineage: dict[str, object],
        persist_vectors: bool = True,
    ) -> ForecastFeatureSnapshotModel:
        if entity.trace_id is None:
            entity.trace_id = uuid4()
        validate_trace_id(entity.trace_id)
        entity.feature_values = dict(feature_values)
        entity.feature_lineage = dict(feature_lineage)
        entity.feature_hash = compute_feature_hash(
            commodity_id=entity.commodity_id,
            as_of_date=entity.as_of_date,
            registry_id=entity.registry_id,
            feature_values=entity.feature_values,
            trace_id=entity.trace_id,
        )
        inserted = self.insert(entity)
        if persist_vectors:
            vector_repo = FeatureVectorRepository(self._session)
            for name, value in sorted(entity.feature_values.items()):
                vector_repo.insert_vector(
                    FeatureVectorModel(
                        feature_set_id=inserted.feature_set_id,
                        feature_name=name[:128],
                        feature_value={"value": value},
                    )
                )
        return inserted

    def update(self, entity: ForecastFeatureSnapshotModel) -> ForecastFeatureSnapshotModel:
        block_immutable_update(self._model)
        return entity  # unreachable


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
