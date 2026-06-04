"""Policy observation validation helpers (PI10 Track B)."""

from __future__ import annotations

from decimal import Decimal

from backend.app.persistence.models.policy import (
    PolicyObservationSource,
    PolicyType,
)
from backend.app.persistence.validation.observation import validate_validation_status
from backend.app.persistence.validation.signal import (
    SignalValidationError,
    validate_bounded_decimal,
    validate_direction,
)

__all__ = [
    "PolicyValidationError",
    "validate_policy_confidence",
    "validate_policy_impact_direction",
    "validate_policy_source",
    "validate_policy_type",
    "validate_validation_status",
]


class PolicyValidationError(ValueError):
    """Raised when policy observation fields fail validation."""


def validate_policy_type(policy_type: str) -> None:
    allowed = {member.value for member in PolicyType}
    if policy_type not in allowed:
        msg = f"policy_type must be one of {sorted(allowed)}, got {policy_type!r}"
        raise PolicyValidationError(msg)


def validate_policy_source(source: str) -> None:
    allowed = {member.value for member in PolicyObservationSource}
    if source not in allowed:
        msg = f"source must be one of {sorted(allowed)}, got {source!r}"
        raise PolicyValidationError(msg)


def validate_policy_impact_direction(impact_direction: str) -> None:
    try:
        validate_direction(impact_direction)
    except SignalValidationError as exc:
        raise PolicyValidationError(str(exc)) from exc


def validate_policy_confidence(confidence: Decimal | float) -> None:
    try:
        validate_bounded_decimal(confidence, field_name="confidence")
    except SignalValidationError as exc:
        raise PolicyValidationError(str(exc)) from exc
