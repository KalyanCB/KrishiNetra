"""Decision stack field validation — TDS-006 §3.12–3.16 (E-01-S07)."""

from __future__ import annotations

from decimal import Decimal

from shared.domain.enums import ActionType, LiquidityNeed, PersonaType


class DecisionValidationError(ValueError):
    """Raised when decision stack fields fail validation."""


def validate_persona_type(value: str) -> None:
    valid = {member.value for member in PersonaType}
    if value not in valid:
        raise DecisionValidationError(
            f"persona_type must be one of {sorted(valid)}, got {value!r}"
        )


def validate_liquidity_need(value: str) -> None:
    valid = {member.value for member in LiquidityNeed}
    if value not in valid:
        raise DecisionValidationError(
            f"liquidity_need must be one of {sorted(valid)}, got {value!r}"
        )


def validate_action_type(value: str) -> None:
    valid = {member.value for member in ActionType}
    if value not in valid:
        raise DecisionValidationError(
            f"action_type must be one of {sorted(valid)}, got {value!r}"
        )


def validate_recommendation_confidence(value: Decimal | float) -> None:
    numeric = float(value)
    if numeric < 0.0 or numeric > 1.0:
        raise DecisionValidationError(
            f"recommendation_confidence must be in [0, 1], got {numeric}"
        )


def validate_user_context_fields(
    *,
    persona_type: str,
    liquidity_need: str,
) -> None:
    validate_persona_type(persona_type)
    validate_liquidity_need(liquidity_need)


def validate_recommendation_version_fields(
    *,
    action_type: str,
    recommendation_confidence: Decimal | float,
) -> None:
    validate_action_type(action_type)
    validate_recommendation_confidence(recommendation_confidence)
