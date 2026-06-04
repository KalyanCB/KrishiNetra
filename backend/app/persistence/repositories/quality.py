"""DataQualitySnapshot repository — TDS-006 §3.17 (E-01-S08)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.repositories.base import BaseRepository
from backend.app.persistence.validation.quality import (
    validate_confidence_penalty,
    validate_quality_score,
)


class DataQualitySnapshotRepository(BaseRepository[DataQualitySnapshotModel]):
    """Append-only quality snapshots keyed by commodity, date, registry."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, DataQualitySnapshotModel)

    def get_snapshot(self, quality_snapshot_id: UUID) -> DataQualitySnapshotModel | None:
        return self._session.get(self._model, quality_snapshot_id)

    def get_by_commodity_date(
        self,
        commodity_id: str,
        as_of_date: date,
        *,
        registry_id: UUID | None = None,
    ) -> DataQualitySnapshotModel | None:
        stmt = select(DataQualitySnapshotModel).where(
            DataQualitySnapshotModel.commodity_id == commodity_id,
            DataQualitySnapshotModel.as_of_date == as_of_date,
        )
        if registry_id is not None:
            stmt = stmt.where(DataQualitySnapshotModel.registry_id == registry_id)
        return self._session.scalars(stmt).first()

    def insert_snapshot(
        self, entity: DataQualitySnapshotModel
    ) -> DataQualitySnapshotModel:
        validate_quality_score(entity.overall_quality_score)
        validate_confidence_penalty(entity.confidence_penalty_factor)
        return self.insert(entity)

    def upsert_snapshot(
        self, entity: DataQualitySnapshotModel
    ) -> DataQualitySnapshotModel:
        """Insert or replace metrics for (commodity_id, as_of_date, registry_id)."""
        validate_quality_score(entity.overall_quality_score)
        validate_confidence_penalty(entity.confidence_penalty_factor)
        existing = self.get_by_commodity_date(
            entity.commodity_id,
            entity.as_of_date,
            registry_id=entity.registry_id,
        )
        if existing is None:
            return self.insert(entity)
        existing.source_health = entity.source_health
        existing.overall_quality_score = entity.overall_quality_score
        existing.agmarknet_lag_hours = entity.agmarknet_lag_hours
        existing.futures_feed_ok = entity.futures_feed_ok
        existing.signals_missing = entity.signals_missing
        existing.confidence_penalty_factor = entity.confidence_penalty_factor
        self._session.flush()
        return existing
