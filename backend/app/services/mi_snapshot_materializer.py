"""Materialize MI snapshot payloads from PostgreSQL and cache in Redis (E-01-S09)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from backend.app.cache.mi_projection import (
    RedisMIProjectionClient,
    build_mi_cache_key,
)
from backend.app.persistence.models.forecast import ForecastVersionModel
from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.models.signal import SignalSnapshotModel
from backend.app.persistence.unit_of_work import UnitOfWork
from shared.contracts.mi_snapshot import MISnapshotPayload


def _horizon_summary(label: str, horizon: dict[str, object] | None) -> dict[str, object] | None:
    if horizon is None:
        return None
    return {
        "horizon": label,
        "point": horizon.get("point"),
        "band_low": horizon.get("band_low"),
        "band_high": horizon.get("band_high"),
        "direction": horizon.get("direction"),
        "forecast_confidence": horizon.get("forecast_confidence"),
    }


def _horizon_confidence(horizon: dict[str, object] | None) -> float | None:
    if horizon is None:
        return None
    value = horizon.get("forecast_confidence")
    if value is None:
        return None
    if isinstance(value, (int, float, str)):
        return float(value)
    return None


def build_mi_payload(
    *,
    snapshot: SignalSnapshotModel,
    forecast: ForecastVersionModel | None,
    quality: DataQualitySnapshotModel | None,
) -> MISnapshotPayload:
    """Build denormalized MI payload from canonical PostgreSQL rows."""
    horizon_summaries = [
        summary
        for summary in (
            _horizon_summary("30", forecast.horizon_30 if forecast else None),
            _horizon_summary("60", forecast.horizon_60 if forecast else None),
            _horizon_summary("90", forecast.horizon_90 if forecast else None),
        )
        if summary is not None
    ]

    return MISnapshotPayload(
        mi_snapshot_id=uuid4(),
        commodity_id=snapshot.commodity_id,
        as_of_date=snapshot.as_of_date,
        registry_id=snapshot.registry_id,
        generated_at=datetime.now(tz=UTC),
        snapshot_id=snapshot.snapshot_id,
        snapshot_hash=snapshot.snapshot_hash,
        forecast_version_id=forecast.forecast_version_id if forecast else None,
        horizon_summaries=horizon_summaries or None,
        forecast_confidence_30=_horizon_confidence(
            forecast.horizon_30 if forecast else None
        ),
        forecast_confidence_60=_horizon_confidence(
            forecast.horizon_60 if forecast else None
        ),
        forecast_confidence_90=_horizon_confidence(
            forecast.horizon_90 if forecast else None
        ),
        data_quality_snapshot_id=snapshot.data_quality_snapshot_id,
        overall_quality_score=(
            float(quality.overall_quality_score) if quality is not None else None
        ),
        partial=True,
    )


class MISnapshotMaterializer:
    """Load canonical rows and publish MI projection to Redis."""

    def __init__(
        self,
        uow: UnitOfWork,
        cache: RedisMIProjectionClient,
    ) -> None:
        self._uow = uow
        self._cache = cache

    def materialize(
        self,
        commodity_id: str,
        as_of_date: date,
        registry_id: UUID,
    ) -> MISnapshotPayload | None:
        """Build payload from PostgreSQL; returns None when snapshot is missing."""
        snapshot = self._uow.signal_snapshots.get_snapshot(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry_id,
        )
        if snapshot is None:
            return None

        forecast = self._uow.forecast_versions.get_published(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry_id,
        )
        quality: DataQualitySnapshotModel | None = None
        if snapshot.data_quality_snapshot_id is not None:
            quality = self._uow.quality_snapshots.get_snapshot(
                snapshot.data_quality_snapshot_id
            )

        return build_mi_payload(snapshot=snapshot, forecast=forecast, quality=quality)

    def materialize_and_cache(
        self,
        commodity_id: str,
        as_of_date: date,
        registry_id: UUID,
    ) -> MISnapshotPayload | None:
        """Materialize from PostgreSQL and write Redis projection (cache-only)."""
        payload = self.materialize(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry_id,
        )
        if payload is None:
            return None

        key = build_mi_cache_key(commodity_id, as_of_date)
        self._cache.set_mi_snapshot(key, payload.model_dump(mode="json"))
        return payload
