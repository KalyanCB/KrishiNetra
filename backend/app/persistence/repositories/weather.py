"""Append-only weather observation repository — PI6 Track C."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.weather import WeatherObservationModel
from backend.app.persistence.repositories.base import BaseRepository
from backend.app.persistence.validation.observation import validate_validation_status
from backend.app.persistence.validation.weather import validate_weather_source


class WeatherObservationRepository(BaseRepository[WeatherObservationModel]):
    """Append-only weather observations; corrections via new row + supersedes_id."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, WeatherObservationModel)

    def insert_observation(
        self, entity: WeatherObservationModel
    ) -> WeatherObservationModel:
        validate_weather_source(entity.source)
        validate_validation_status(entity.validation_status)
        return self.insert(entity)

    def get_observation(
        self, observation_id: UUID, *, as_of_date: date
    ) -> WeatherObservationModel | None:
        return self._session.get(self._model, (observation_id, as_of_date))

    def list_by_region_date_range(
        self,
        region_id: str,
        start: date,
        end: date,
    ) -> list[WeatherObservationModel]:
        stmt = (
            select(WeatherObservationModel)
            .where(
                WeatherObservationModel.region_id == region_id,
                WeatherObservationModel.as_of_date >= start,
                WeatherObservationModel.as_of_date <= end,
            )
            .order_by(WeatherObservationModel.as_of_date.desc())
        )
        return list(self._session.scalars(stmt).all())

    def list_by_commodity_date_range(
        self,
        commodity_id: str,
        start: date,
        end: date,
        *,
        source: str | None = None,
    ) -> list[WeatherObservationModel]:
        stmt = select(WeatherObservationModel).where(
            WeatherObservationModel.commodity_id == commodity_id,
            WeatherObservationModel.as_of_date >= start,
            WeatherObservationModel.as_of_date <= end,
        )
        if source is not None:
            stmt = stmt.where(WeatherObservationModel.source == source)
        stmt = stmt.order_by(WeatherObservationModel.as_of_date.desc())
        return list(self._session.scalars(stmt).all())
