"""Append-only futures observation repository — PI10 Track A."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.futures import FuturesObservationModel
from backend.app.persistence.repositories.base import BaseRepository
from backend.app.persistence.validation.futures import (
    validate_environment,
    validate_futures_source,
    validate_settle_price,
    validate_validation_status,
)


class FuturesObservationRepository(BaseRepository[FuturesObservationModel]):
    """Append-only futures observations; corrections via new row + supersedes_id."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, FuturesObservationModel)

    def insert_observation(
        self, entity: FuturesObservationModel
    ) -> FuturesObservationModel:
        validate_futures_source(entity.source)
        validate_environment(entity.environment)
        validate_settle_price(entity.settle_price)
        validate_validation_status(entity.validation_status)
        return self.insert(entity)

    def get_observation(
        self, observation_id: UUID, *, as_of_date: date
    ) -> FuturesObservationModel | None:
        return self._session.get(self._model, (observation_id, as_of_date))

    def list_by_commodity_date_range(
        self,
        commodity_id: str,
        start: date,
        end: date,
        *,
        source: str | None = None,
    ) -> list[FuturesObservationModel]:
        stmt = select(FuturesObservationModel).where(
            FuturesObservationModel.commodity_id == commodity_id,
            FuturesObservationModel.as_of_date >= start,
            FuturesObservationModel.as_of_date <= end,
        )
        if source is not None:
            stmt = stmt.where(FuturesObservationModel.source == source)
        stmt = stmt.order_by(
            FuturesObservationModel.as_of_date.desc(),
            FuturesObservationModel.expiry_date.asc(),
        )
        return list(self._session.scalars(stmt).all())
