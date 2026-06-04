"""Observation validation helpers (E-01-S04)."""

from __future__ import annotations

from backend.app.persistence.models.observation import ObservationValidationStatus


class ObservationValidationError(ValueError):
    """Raised when observation fields fail validation."""


def validate_validation_status(status: str) -> None:
    """Ensure status is a known observation_validation_status value."""
    allowed = {member.value for member in ObservationValidationStatus}
    if status not in allowed:
        msg = f"validation_status must be one of {sorted(allowed)}, got {status!r}"
        raise ObservationValidationError(msg)
