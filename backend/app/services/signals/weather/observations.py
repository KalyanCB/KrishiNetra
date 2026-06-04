"""Load and index weather observations for signal generation."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import ObservationValidationStatus
from backend.app.persistence.models.weather import WeatherObservationModel
from backend.app.persistence.repositories.weather import WeatherObservationRepository
from backend.app.services.signals.weather.constants import (
    CLIMATOLOGY_DAYS,
    TELANGANA_WEATHER_REGION_IDS,
)

USABLE_VALIDATION_STATUSES = frozenset(
    {
        ObservationValidationStatus.VALIDATED.value,
        ObservationValidationStatus.PUBLISHED.value,
        ObservationValidationStatus.RECEIVED.value,
    }
)

_STATUS_RANK: dict[str, int] = {
    ObservationValidationStatus.VALIDATED.value: 3,
    ObservationValidationStatus.PUBLISHED.value: 2,
    ObservationValidationStatus.RECEIVED.value: 1,
}


@dataclass(frozen=True, slots=True)
class RegionalDailyWeather:
    """Regional mean weather for one as_of_date (equal-weight district rollup)."""

    as_of_date: date
    rainfall_mm: Decimal
    temperature_mean_c: Decimal | None
    relative_humidity_pct: Decimal | None
    observation_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WeatherObservationSeries:
    """Indexed regional daily series through as_of_date."""

    as_of_date: date
    by_date: dict[date, RegionalDailyWeather]
    regions_expected: int
    regions_reporting: int
    source_observation_refs: tuple[str, ...]


class WeatherSignalInputError(ValueError):
    """Raised when observations are insufficient for signal generation."""


def _status_rank(status: str) -> int:
    return _STATUS_RANK.get(status, 0)


def select_observations(
    rows: list[WeatherObservationModel],
    *,
    region_ids: tuple[str, ...],
    as_of_date: date,
) -> list[WeatherObservationModel]:
    """Prefer validated over received for each region on as_of_date."""
    best: dict[str, WeatherObservationModel] = {}
    for row in rows:
        if row.region_id not in region_ids:
            continue
        if row.as_of_date != as_of_date:
            continue
        if row.validation_status not in USABLE_VALIDATION_STATUSES:
            continue
        if row.rainfall_mm is None:
            continue
        current = best.get(row.region_id)
        if current is None or _status_rank(row.validation_status) > _status_rank(
            current.validation_status
        ):
            best[row.region_id] = row
    return list(best.values())


def load_observation_series(
    session: Session,
    *,
    commodity_id: str,
    as_of_date: date,
    region_ids: tuple[str, ...] = TELANGANA_WEATHER_REGION_IDS,
    source: str | None = None,
) -> WeatherObservationSeries:
    """Load regional daily rollups from as_of_date - CLIMATOLOGY through as_of_date."""
    start = as_of_date - timedelta(days=CLIMATOLOGY_DAYS)
    repo = WeatherObservationRepository(session)
    rows = repo.list_by_commodity_date_range(
        commodity_id,
        start,
        as_of_date,
        source=source,
    )
    usable = [r for r in rows if r.validation_status in USABLE_VALIDATION_STATUSES]
    if not usable:
        msg = (
            f"no usable weather observations for {commodity_id!r} "
            f"through {as_of_date.isoformat()}"
        )
        raise WeatherSignalInputError(msg)

    by_region_date: dict[tuple[str, date], WeatherObservationModel] = {}
    for row in usable:
        if row.region_id not in region_ids:
            continue
        if row.rainfall_mm is None:
            continue
        key = (row.region_id, row.as_of_date)
        current = by_region_date.get(key)
        if current is None or _status_rank(row.validation_status) > _status_rank(
            current.validation_status
        ):
            by_region_date[key] = row

    daily_buckets: dict[date, list[WeatherObservationModel]] = defaultdict(list)
    for (_, day), row in by_region_date.items():
        if day <= as_of_date:
            daily_buckets[day].append(row)

    by_date: dict[date, RegionalDailyWeather] = {}
    refs: list[str] = []
    for day, day_rows in sorted(daily_buckets.items()):
        rainfall_values = [row.rainfall_mm for row in day_rows if row.rainfall_mm is not None]
        if not rainfall_values:
            continue
        rain_mean = sum(rainfall_values, start=Decimal("0")) / Decimal(len(rainfall_values))
        temps = [
            row.temperature_mean_c
            for row in day_rows
            if row.temperature_mean_c is not None
        ]
        humidity = [
            row.relative_humidity_pct
            for row in day_rows
            if row.relative_humidity_pct is not None
        ]
        temp_mean = (
            sum(temps, start=Decimal("0")) / Decimal(len(temps)) if temps else None
        )
        rh_mean = (
            sum(humidity, start=Decimal("0")) / Decimal(len(humidity))
            if humidity
            else None
        )
        day_refs = tuple(str(row.observation_id) for row in day_rows)
        refs.extend(day_refs)
        by_date[day] = RegionalDailyWeather(
            as_of_date=day,
            rainfall_mm=rain_mean,
            temperature_mean_c=temp_mean,
            relative_humidity_pct=rh_mean,
            observation_ids=day_refs,
        )

    regions_reporting = sum(
        1
        for region_id in region_ids
        if any(
            row.region_id == region_id and row.as_of_date == as_of_date
            for row in by_region_date.values()
        )
    )

    return WeatherObservationSeries(
        as_of_date=as_of_date,
        by_date=by_date,
        regions_expected=len(region_ids),
        regions_reporting=regions_reporting,
        source_observation_refs=tuple(sorted(set(refs))),
    )
