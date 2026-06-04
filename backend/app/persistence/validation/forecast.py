"""ForecastVersion and horizon JSON validation — TDS-006 §3.11 (E-01-S06)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from shared.domain.enums import Direction


class ForecastValidationError(ValueError):
    """Raised when forecast fields fail validation."""


HORIZON_FIELDS = ("horizon_30", "horizon_60", "horizon_90")
HORIZON_JSON_KEYS = (
    "point",
    "band_low",
    "band_high",
    "direction",
    "forecast_confidence",
)


def validate_direction(direction: str) -> None:
    valid = {member.value for member in Direction}
    if direction not in valid:
        raise ForecastValidationError(
            f"direction must be one of {sorted(valid)}, got {direction!r}"
        )


def validate_forecast_confidence(value: Decimal | float, *, field_name: str) -> None:
    numeric = float(value)
    if numeric < 0.0 or numeric > 1.0:
        raise ForecastValidationError(
            f"{field_name} must be in [0, 1], got {numeric}"
        )


def validate_horizon_payload(horizon: dict[str, Any] | None, *, field_name: str) -> None:
    if horizon is None:
        return
    missing = [key for key in HORIZON_JSON_KEYS if key not in horizon]
    if missing:
        raise ForecastValidationError(
            f"{field_name} missing required keys: {missing}"
        )
    validate_direction(str(horizon["direction"]))
    validate_forecast_confidence(
        horizon["forecast_confidence"],
        field_name=f"{field_name}.forecast_confidence",
    )


def validate_forecast_version_horizons(
    *,
    horizon_30: dict[str, Any] | None,
    horizon_60: dict[str, Any] | None,
    horizon_90: dict[str, Any] | None,
) -> None:
    validate_horizon_payload(horizon_30, field_name="horizon_30")
    validate_horizon_payload(horizon_60, field_name="horizon_60")
    validate_horizon_payload(horizon_90, field_name="horizon_90")
