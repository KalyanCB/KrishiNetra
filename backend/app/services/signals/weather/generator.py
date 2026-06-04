"""WeatherSignalGenerator — deterministic StructuredSignal for cotton belt (E-04-S02)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.app.persistence.models.signal import StructuredSignalModel
from backend.app.persistence.repositories.signal import StructuredSignalRepository
from backend.app.services.ingest.weather.constants import WEATHER_SOURCE_NASA_POWER
from backend.app.services.registry.cotton_config import COTTON_COMMODITY_ID
from backend.app.services.signals.common import signed_value
from backend.app.services.signals.weather.constants import AGENT_VERSION
from backend.app.services.signals.weather.features import compute_weather_features
from backend.app.services.signals.weather.observations import (
    WeatherSignalInputError,
    load_observation_series,
)
from shared.domain.enums import AgentType

DEFAULT_SIGNAL_HOUR = 12


class WeatherSignalGenerator:
    """Emit one Weather StructuredSignal per daily refresh (TDS-004 §4.2)."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._signal_repo = StructuredSignalRepository(session)

    def generate(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        as_of_date: date,
        registry_id: UUID,
        source: str | None = WEATHER_SOURCE_NASA_POWER,
        as_of_timestamp: datetime | None = None,
        trace_id: UUID | None = None,
    ) -> StructuredSignalModel:
        """Compute Weather agent output without persisting."""
        series = load_observation_series(
            self._session,
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            source=source,
        )
        features = compute_weather_features(series)
        timestamp = as_of_timestamp or datetime(
            as_of_date.year,
            as_of_date.month,
            as_of_date.day,
            DEFAULT_SIGNAL_HOUR,
            0,
            tzinfo=UTC,
        )

        value = signed_value(direction=features.direction, magnitude=features.magnitude)
        components = features.as_components()
        components["source"] = source or "mixed"

        return StructuredSignalModel(
            signal_id=uuid4(),
            agent_type=AgentType.WEATHER.value,
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            as_of_timestamp=timestamp,
            value=value,
            direction=features.direction,
            magnitude=features.magnitude,
            confidence=features.confidence,
            signal_components=components,
            source_observation_refs=list(series.source_observation_refs),
            registry_id=registry_id,
            agent_version=AGENT_VERSION,
            trace_id=trace_id,
        )

    def persist(self, signal: StructuredSignalModel) -> StructuredSignalModel:
        """Append-only insert via StructuredSignalRepository."""
        return self._signal_repo.insert_signal(signal)

    def generate_and_persist(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        as_of_date: date,
        registry_id: UUID,
        source: str | None = WEATHER_SOURCE_NASA_POWER,
        as_of_timestamp: datetime | None = None,
        trace_id: UUID | None = None,
    ) -> StructuredSignalModel:
        """Compute and persist a Weather StructuredSignal."""
        signal = self.generate(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry_id,
            source=source,
            as_of_timestamp=as_of_timestamp,
            trace_id=trace_id,
        )
        return self.persist(signal)


def weather_signal_value(
    *,
    direction: str,
    magnitude: Decimal,
) -> Decimal:
    """Expose signed value helper for tests."""
    return signed_value(direction=direction, magnitude=magnitude)


__all__ = [
    "WeatherSignalGenerator",
    "WeatherSignalInputError",
    "weather_signal_value",
]
