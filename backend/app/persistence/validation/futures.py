"""Futures observation validation helpers (PI10 Track A)."""

from __future__ import annotations

from decimal import Decimal

from backend.app.persistence.models.futures import (
    FuturesEnvironment,
    FuturesObservationSource,
)
from backend.app.persistence.validation.observation import validate_validation_status

__all__ = [
    "FuturesValidationError",
    "validate_environment",
    "validate_futures_source",
    "validate_settle_price",
    "validate_validation_status",
]

MAX_SETTLE_PRICE_INR = 1_000_000.0


class FuturesValidationError(ValueError):
    """Raised when futures observation fields fail validation."""


def validate_futures_source(source: str) -> None:
    """Ensure source is a known futures ingest identifier."""
    allowed = {member.value for member in FuturesObservationSource}
    if source not in allowed:
        msg = f"source must be one of {sorted(allowed)}, got {source!r}"
        raise FuturesValidationError(msg)


def validate_environment(environment: str) -> None:
    """Ensure environment label matches prototype/production guardrails."""
    allowed = {member.value for member in FuturesEnvironment}
    if environment not in allowed:
        msg = f"environment must be one of {sorted(allowed)}, got {environment!r}"
        raise FuturesValidationError(msg)


def validate_settle_price(value: Decimal | float) -> None:
    """Sanity-check settlement price (₹/20 kg)."""
    amount = float(value)
    if amount <= 0:
        raise FuturesValidationError(f"settle_price must be > 0, got {amount}")
    if amount > MAX_SETTLE_PRICE_INR:
        raise FuturesValidationError(
            f"settle_price exceeds cap {MAX_SETTLE_PRICE_INR}, got {amount}"
        )
