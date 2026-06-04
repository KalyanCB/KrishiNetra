"""Shared deterministic helpers for E-04 signal generators."""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from shared.domain.enums import Direction

FOUR_DP = Decimal("0.0001")
TWO_DP = Decimal("0.01")


def quantize(value: Decimal, *, exp: Decimal = FOUR_DP) -> Decimal:
    """Round for stable replay hashes (NFR-TRC-001)."""
    return value.quantize(exp, rounding=ROUND_HALF_UP)


def clip_unit(value: Decimal) -> Decimal:
    """Clip to [0, 1] for magnitude/confidence components."""
    if value < Decimal("0"):
        return Decimal("0")
    if value > Decimal("1"):
        return Decimal("1")
    return quantize(value)


def clip_signed(value: Decimal) -> Decimal:
    """Clip to [-1, 1] for normalized deviation components."""
    if value < Decimal("-1"):
        return Decimal("-1")
    if value > Decimal("1"):
        return Decimal("1")
    return quantize(value)


def direction_sign(direction: str) -> Decimal:
    """Map TDS-004 direction to signed multiplier."""
    if direction == Direction.BULLISH.value:
        return Decimal("1")
    if direction == Direction.BEARISH.value:
        return Decimal("-1")
    return Decimal("0")


def signed_value(*, direction: str, magnitude: Decimal) -> Decimal:
    """value = sign(direction) × magnitude (SIGNAL_ENGINE_V1 §2)."""
    return quantize(direction_sign(direction) * magnitude)
