"""DataQualitySnapshot validation — TDS-006 §3.17 / TDS-011 (E-01-S08)."""

from __future__ import annotations

from decimal import Decimal


class QualityValidationError(ValueError):
    """Raised when quality snapshot fields fail validation."""


def validate_quality_score(score: Decimal | float) -> None:
    """overall_quality_score must be in [0, 1]."""
    value = float(score)
    if value < 0.0 or value > 1.0:
        raise QualityValidationError(
            f"overall_quality_score must be in [0, 1], got {value}"
        )


def validate_confidence_penalty(factor: Decimal | float) -> None:
    """confidence_penalty_factor must be in [0, 1]."""
    value = float(factor)
    if value < 0.0 or value > 1.0:
        raise QualityValidationError(
            f"confidence_penalty_factor must be in [0, 1], got {value}"
        )
