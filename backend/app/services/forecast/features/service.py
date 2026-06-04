"""ForecastFeatureSnapshot persistence service — PI10 Track C (storage only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.app.persistence.models.forecast import ForecastFeatureSnapshotModel
from backend.app.persistence.models.signal import StructuredSignalModel
from backend.app.persistence.repositories.forecast import (
    ForecastFeatureSnapshotRepository,
)
from backend.app.services.forecast.features.assembler import assemble_forecast_features


@dataclass(frozen=True, slots=True)
class ForecastFeaturePersistResult:
    """Outcome of persist_from_signals."""

    snapshot: ForecastFeatureSnapshotModel
    feature_values: dict[str, object]
    feature_lineage: dict[str, object]


class ForecastFeatureStoreService:
    """
    Assemble and persist ForecastFeatureSnapshot rows from agent signals.

    No forecast model inference — feature storage and lineage only.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ForecastFeatureSnapshotRepository(session)

    def persist_from_signals(
        self,
        *,
        commodity_id: str,
        as_of_date: date,
        registry_id: UUID,
        market: StructuredSignalModel | None,
        weather: StructuredSignalModel | None,
        futures: StructuredSignalModel | None = None,
        use_futures_stub: bool = True,
        trace_id: UUID | None = None,
        snapshot_trace_id: UUID | None = None,
        persist_vectors: bool = True,
    ) -> ForecastFeaturePersistResult:
        feature_values, feature_lineage = assemble_forecast_features(
            as_of_date=as_of_date,
            market=market,
            weather=weather,
            futures=futures,
            session=self._session,
            commodity_id=commodity_id,
            use_futures_stub=use_futures_stub,
            snapshot_trace_id=snapshot_trace_id,
        )
        entity = ForecastFeatureSnapshotModel(
            feature_set_id=uuid4(),
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry_id,
            feature_hash="",
            trace_id=trace_id,
        )
        snapshot = self._repo.insert_snapshot(
            entity,
            feature_values=feature_values,
            feature_lineage=feature_lineage,
            persist_vectors=persist_vectors,
        )
        return ForecastFeaturePersistResult(
            snapshot=snapshot,
            feature_values=feature_values,
            feature_lineage=feature_lineage,
        )

    def get_snapshot(
        self,
        commodity_id: str,
        as_of_date: date,
        registry_id: UUID,
    ) -> ForecastFeatureSnapshotModel | None:
        return self._repo.get_snapshot(commodity_id, as_of_date, registry_id)

    def get_snapshot_by_trace_id(
        self, trace_id: UUID
    ) -> ForecastFeatureSnapshotModel | None:
        return self._repo.get_snapshot_by_trace_id(trace_id)
