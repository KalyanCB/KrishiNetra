"""StructuredSignal and SignalSnapshot repositories — TDS-006 §3.8–3.9 (E-01-S05)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.signal import (
    SignalSnapshotModel,
    StructuredSignalModel,
)
from backend.app.persistence.repositories.base import BaseRepository
from backend.app.persistence.validation.signal import (
    compute_snapshot_hash,
    validate_agent_type,
    validate_bounded_decimal,
    validate_direction,
)


class StructuredSignalRepository(BaseRepository[StructuredSignalModel]):
    """Insert-only structured signals; one row per agent per commodity/day/registry."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, StructuredSignalModel)

    def insert_signal(self, entity: StructuredSignalModel) -> StructuredSignalModel:
        validate_agent_type(entity.agent_type)
        validate_direction(entity.direction)
        validate_bounded_decimal(entity.magnitude, field_name="magnitude")
        validate_bounded_decimal(entity.confidence, field_name="confidence")
        return self.insert(entity)

    def get_signal(
        self, signal_id: UUID, *, as_of_date: date
    ) -> StructuredSignalModel | None:
        return self._session.get(self._model, (signal_id, as_of_date))

    def list_by_commodity_date(
        self,
        commodity_id: str,
        as_of_date: date,
        *,
        registry_id: UUID,
    ) -> list[StructuredSignalModel]:
        stmt = (
            select(StructuredSignalModel)
            .where(
                StructuredSignalModel.commodity_id == commodity_id,
                StructuredSignalModel.as_of_date == as_of_date,
                StructuredSignalModel.registry_id == registry_id,
            )
            .order_by(StructuredSignalModel.agent_type)
        )
        return list(self._session.scalars(stmt).all())


class SignalSnapshotRepository(BaseRepository[SignalSnapshotModel]):
    """Insert-only daily signal bundles for replay and forecast input."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, SignalSnapshotModel)

    def get_snapshot(
        self,
        commodity_id: str,
        as_of_date: date,
        registry_id: UUID,
    ) -> SignalSnapshotModel | None:
        stmt = select(SignalSnapshotModel).where(
            SignalSnapshotModel.commodity_id == commodity_id,
            SignalSnapshotModel.as_of_date == as_of_date,
            SignalSnapshotModel.registry_id == registry_id,
        )
        return self._session.scalars(stmt).first()

    def insert_snapshot(
        self,
        entity: SignalSnapshotModel,
        *,
        signal_payloads: list[dict[str, object]],
    ) -> SignalSnapshotModel:
        entity.snapshot_hash = compute_snapshot_hash(
            commodity_id=entity.commodity_id,
            as_of_date=entity.as_of_date,
            registry_id=entity.registry_id,
            signals=signal_payloads,
        )
        return self.insert(entity)
