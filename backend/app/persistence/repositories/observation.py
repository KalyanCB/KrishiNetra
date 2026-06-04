"""Append-only observation repositories — TDS-006 §3.6–3.7 (E-01-S04)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    PriceObservationModel,
)
from backend.app.persistence.repositories.base import BaseRepository
from backend.app.persistence.validation.observation import validate_validation_status


class PriceObservationRepository(BaseRepository[PriceObservationModel]):
    """Append-only price observations; corrections via new row + supersedes_id."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, PriceObservationModel)

    def insert_observation(self, entity: PriceObservationModel) -> PriceObservationModel:
        validate_validation_status(entity.validation_status)
        return self.insert(entity)

    def get_observation(
        self, observation_id: UUID, *, as_of_date: date
    ) -> PriceObservationModel | None:
        return self._session.get(self._model, (observation_id, as_of_date))

    def list_by_commodity_date_range(
        self,
        commodity_id: str,
        start: date,
        end: date,
    ) -> list[PriceObservationModel]:
        stmt = (
            select(PriceObservationModel)
            .where(
                PriceObservationModel.commodity_id == commodity_id,
                PriceObservationModel.as_of_date >= start,
                PriceObservationModel.as_of_date <= end,
            )
            .order_by(PriceObservationModel.as_of_date.desc())
        )
        return list(self._session.scalars(stmt).all())


class ArrivalObservationRepository(BaseRepository[ArrivalObservationModel]):
    """Append-only arrival observations; corrections via new row + supersedes_id."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, ArrivalObservationModel)

    def insert_observation(
        self, entity: ArrivalObservationModel
    ) -> ArrivalObservationModel:
        validate_validation_status(entity.validation_status)
        return self.insert(entity)

    def get_observation(
        self, observation_id: UUID, *, as_of_date: date
    ) -> ArrivalObservationModel | None:
        return self._session.get(self._model, (observation_id, as_of_date))

    def list_by_commodity_date_range(
        self,
        commodity_id: str,
        start: date,
        end: date,
    ) -> list[ArrivalObservationModel]:
        stmt = (
            select(ArrivalObservationModel)
            .where(
                ArrivalObservationModel.commodity_id == commodity_id,
                ArrivalObservationModel.as_of_date >= start,
                ArrivalObservationModel.as_of_date <= end,
            )
            .order_by(ArrivalObservationModel.as_of_date.desc())
        )
        return list(self._session.scalars(stmt).all())
