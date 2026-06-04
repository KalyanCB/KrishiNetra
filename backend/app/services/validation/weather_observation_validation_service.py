"""Batch weather observation validation (PI9 E-03 parallel, non-blocking)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import ObservationValidationStatus
from backend.app.persistence.models.reference import CommodityModel, RegionModel
from backend.app.persistence.models.weather import WeatherObservationModel
from backend.app.persistence.validation.weather import (
    WeatherValidationError,
    validate_rainfall_mm,
    validate_temperature_mean_c,
    validate_weather_source,
)
from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID
from backend.app.services.ingest.weather.constants import WEATHER_SOURCE_NASA_POWER
from backend.app.services.validation.observation_validation_service import (
    BULK_UPDATE_CHUNK_SIZE,
    PENDING_VALIDATION_STATUSES,
    RowValidationSummary,
)


@dataclass(frozen=True, slots=True)
class WeatherBatchValidationResult:
    """Outcome of a weather-only batch validation run."""

    weather: RowValidationSummary

    @property
    def total_examined(self) -> int:
        return self.weather.examined

    @property
    def total_validated(self) -> int:
        return self.weather.validated

    @property
    def total_rejected(self) -> int:
        return self.weather.rejected


class WeatherObservationValidationService:
    """Promote pending NASA POWER weather rows from received to validated/rejected."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def validate_pending(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        source: str = WEATHER_SOURCE_NASA_POWER,
        window_start: date | None = None,
        window_end: date | None = None,
        dry_run: bool = False,
    ) -> WeatherBatchValidationResult:
        """Validate received weather rows; update status unless dry_run."""
        known_regions, known_commodities = self._load_reference_ids()
        weather_summary = self._validate_weather(
            commodity_id=commodity_id,
            source=source,
            window_start=window_start,
            window_end=window_end,
            known_region_ids=known_regions,
            known_commodity_ids=known_commodities,
            dry_run=dry_run,
        )
        return WeatherBatchValidationResult(weather=weather_summary)

    def count_pending(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        source: str = WEATHER_SOURCE_NASA_POWER,
        window_start: date | None = None,
        window_end: date | None = None,
    ) -> int:
        filters = [
            WeatherObservationModel.source == source,
            WeatherObservationModel.commodity_id == commodity_id,
            WeatherObservationModel.validation_status.in_(PENDING_VALIDATION_STATUSES),
        ]
        if window_start is not None:
            filters.append(WeatherObservationModel.as_of_date >= window_start)
        if window_end is not None:
            filters.append(WeatherObservationModel.as_of_date <= window_end)
        return int(
            self._session.scalar(
                select(func.count())
                .select_from(WeatherObservationModel)
                .where(*filters)
            )
            or 0
        )

    def _load_reference_ids(self) -> tuple[frozenset[str], frozenset[str]]:
        region_ids = frozenset(
            self._session.scalars(select(RegionModel.region_id)).all()
        )
        commodity_ids = frozenset(
            self._session.scalars(select(CommodityModel.commodity_id)).all()
        )
        return region_ids, commodity_ids

    def _validate_weather(
        self,
        *,
        commodity_id: str,
        source: str,
        window_start: date | None,
        window_end: date | None,
        known_region_ids: frozenset[str],
        known_commodity_ids: frozenset[str],
        dry_run: bool,
    ) -> RowValidationSummary:
        stmt = self._pending_weather_stmt(
            commodity_id=commodity_id,
            source=source,
            window_start=window_start,
            window_end=window_end,
        )
        rows = list(self._session.scalars(stmt).all())
        validated = 0
        rejected = 0
        issue_counts: dict[str, int] = {}
        validated_ids: list[UUID] = []
        rejected_ids: list[UUID] = []

        for row in rows:
            if row.commodity_id not in known_commodity_ids:
                rejected += 1
                issue_counts["unknown_commodity"] = (
                    issue_counts.get("unknown_commodity", 0) + 1
                )
                rejected_ids.append(row.observation_id)
                continue
            if row.region_id not in known_region_ids:
                rejected += 1
                issue_counts["unknown_region"] = (
                    issue_counts.get("unknown_region", 0) + 1
                )
                rejected_ids.append(row.observation_id)
                continue
            try:
                validate_weather_source(row.source)
                validate_rainfall_mm(row.rainfall_mm)
                validate_temperature_mean_c(row.temperature_mean_c)
            except WeatherValidationError as exc:
                rejected += 1
                key = type(exc).__name__
                issue_counts[key] = issue_counts.get(key, 0) + 1
                rejected_ids.append(row.observation_id)
            else:
                validated += 1
                validated_ids.append(row.observation_id)

        if not dry_run:
            self._bulk_set_weather_status(
                validated_ids, ObservationValidationStatus.VALIDATED.value
            )
            self._bulk_set_weather_status(
                rejected_ids, ObservationValidationStatus.REJECTED.value
            )
            self._session.flush()

        return RowValidationSummary(
            table="weather_observation",
            examined=len(rows),
            validated=validated,
            rejected=rejected,
            skipped=0,
            issue_counts=issue_counts,
        )

    @staticmethod
    def _pending_weather_stmt(
        *,
        commodity_id: str,
        source: str,
        window_start: date | None,
        window_end: date | None,
    ) -> Select[tuple[WeatherObservationModel]]:
        stmt = select(WeatherObservationModel).where(
            WeatherObservationModel.source == source,
            WeatherObservationModel.commodity_id == commodity_id,
            WeatherObservationModel.validation_status.in_(PENDING_VALIDATION_STATUSES),
        )
        if window_start is not None:
            stmt = stmt.where(WeatherObservationModel.as_of_date >= window_start)
        if window_end is not None:
            stmt = stmt.where(WeatherObservationModel.as_of_date <= window_end)
        return stmt.order_by(WeatherObservationModel.as_of_date)

    def _bulk_set_weather_status(
        self, observation_ids: list[UUID], status: str
    ) -> None:
        for offset in range(0, len(observation_ids), BULK_UPDATE_CHUNK_SIZE):
            chunk = observation_ids[offset : offset + BULK_UPDATE_CHUNK_SIZE]
            if not chunk:
                continue
            self._session.execute(
                update(WeatherObservationModel)
                .where(WeatherObservationModel.observation_id.in_(chunk))
                .values(validation_status=status)
            )
