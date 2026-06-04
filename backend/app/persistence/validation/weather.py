"""Weather observation validation helpers (PI6 Track C)."""

from __future__ import annotations

from decimal import Decimal

from backend.app.persistence.models.weather import WeatherObservationSource
from backend.app.persistence.validation.observation import validate_validation_status

__all__ = [
    "WeatherValidationError",
    "MAX_DAILY_RAINFALL_MM",
    "MAX_TEMPERATURE_C",
    "MIN_TEMPERATURE_C",
    "validate_rainfall_mm",
    "validate_temperature_mean_c",
    "validate_validation_status",
    "validate_weather_source",
]

MAX_DAILY_RAINFALL_MM = 500.0
MIN_TEMPERATURE_C = -5.0
MAX_TEMPERATURE_C = 55.0


class WeatherValidationError(ValueError):
    """Raised when weather observation fields fail validation."""


def validate_weather_source(source: str) -> None:
    """Ensure source is a known weather ingest identifier."""
    allowed = {member.value for member in WeatherObservationSource}
    if source not in allowed:
        msg = f"source must be one of {sorted(allowed)}, got {source!r}"
        raise WeatherValidationError(msg)


def validate_rainfall_mm(value: Decimal | float | None) -> None:
    """Sanity-check daily rainfall (mm); required for NASA POWER ingest rows."""
    if value is None:
        raise WeatherValidationError("rainfall_mm is required")
    amount = float(value)
    if amount < 0:
        raise WeatherValidationError(f"rainfall_mm must be >= 0, got {amount}")
    if amount > MAX_DAILY_RAINFALL_MM:
        raise WeatherValidationError(
            f"rainfall_mm exceeds daily cap {MAX_DAILY_RAINFALL_MM}, got {amount}"
        )


def validate_temperature_mean_c(value: Decimal | float | None) -> None:
    """Sanity-check mean 2m temperature (°C); NASA POWER maps T2M here."""
    if value is None:
        raise WeatherValidationError("temperature_mean_c is required")
    temp = float(value)
    if temp < MIN_TEMPERATURE_C or temp > MAX_TEMPERATURE_C:
        raise WeatherValidationError(
            f"temperature_mean_c must be in [{MIN_TEMPERATURE_C}, {MAX_TEMPERATURE_C}], "
            f"got {temp}"
        )
