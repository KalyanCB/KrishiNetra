"""Map NASA POWER daily points to weather observation models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from backend.app.persistence.models.observation import ObservationValidationStatus
from backend.app.persistence.models.weather import (
    WeatherObservationModel,
    WeatherObservationSource,
)
from backend.app.persistence.validation.weather import (
    validate_rainfall_mm,
    validate_temperature_mean_c,
)
from backend.app.services.ingest.weather.constants import (
    COTTON_COMMODITY_ID,
    region_id_for_district,
)
from backend.app.spike.weather.nasa_power import NasaPowerDailyPoint


@dataclass(frozen=True, slots=True)
class WeatherObservationDraft:
    """In-memory row before dedupe and append-only insert."""

    observation_id: UUID
    region_id: str
    commodity_id: str
    district_name: str
    as_of_date: date
    rainfall_mm: Decimal
    temperature_mean_c: Decimal
    relative_humidity_pct: Decimal
    observed_at: datetime
    source: str
    provenance: dict[str, object]


def map_nasa_power_point(point: NasaPowerDailyPoint) -> WeatherObservationDraft:
    """Validate and map one NASA POWER daily point to an ingest draft."""
    validate_rainfall_mm(point.precipitation_mm)
    validate_temperature_mean_c(point.temperature_c)
    observed_at = datetime(
        point.observation_date.year,
        point.observation_date.month,
        point.observation_date.day,
        12,
        0,
        tzinfo=UTC,
    )
    return WeatherObservationDraft(
        observation_id=uuid4(),
        region_id=region_id_for_district(point.district),
        commodity_id=COTTON_COMMODITY_ID,
        district_name=point.district,
        as_of_date=point.observation_date,
        rainfall_mm=Decimal(str(round(point.precipitation_mm, 4))),
        temperature_mean_c=Decimal(str(round(point.temperature_c, 2))),
        relative_humidity_pct=Decimal(str(round(point.relative_humidity_pct, 2))),
        observed_at=observed_at,
        source=WeatherObservationSource.NASA_POWER.value,
        provenance={
            "api": "nasa_power_daily_point",
            "latitude": point.latitude,
            "longitude": point.longitude,
            "parameters": ["PRECTOTCORR", "T2M", "RH2M"],
            "community": "AG",
        },
    )


def weather_model_from_draft(draft: WeatherObservationDraft) -> WeatherObservationModel:
    """Build ORM entity for WeatherObservationRepository."""
    return WeatherObservationModel(
        observation_id=draft.observation_id,
        region_id=draft.region_id,
        commodity_id=draft.commodity_id,
        district_name=draft.district_name,
        as_of_date=draft.as_of_date,
        rainfall_mm=draft.rainfall_mm,
        temperature_mean_c=draft.temperature_mean_c,
        relative_humidity_pct=draft.relative_humidity_pct,
        observed_at=draft.observed_at,
        source=draft.source,
        provenance=draft.provenance,
        validation_status=ObservationValidationStatus.RECEIVED.value,
    )
