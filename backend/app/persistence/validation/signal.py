"""StructuredSignal and SignalSnapshot validation — TDS-006 §3.8 (E-01-S05)."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from shared.domain.enums import AgentType, Direction


class SignalValidationError(ValueError):
    """Raised when signal fields fail validation."""


def validate_agent_type(agent_type: str) -> None:
    valid = {member.value for member in AgentType}
    if agent_type not in valid:
        raise SignalValidationError(
            f"agent_type must be one of {sorted(valid)}, got {agent_type!r}"
        )


def validate_direction(direction: str) -> None:
    valid = {member.value for member in Direction}
    if direction not in valid:
        raise SignalValidationError(
            f"direction must be one of {sorted(valid)}, got {direction!r}"
        )


def validate_bounded_decimal(
    value: Decimal | float,
    *,
    field_name: str,
) -> None:
    numeric = float(value)
    if numeric < 0.0 or numeric > 1.0:
        raise SignalValidationError(f"{field_name} must be in [0, 1], got {numeric}")


def signal_hash_payload(
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    signals: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build canonical dict for snapshot_hash (REQ-103 prep)."""
    normalized = []
    for signal in signals:
        components = signal.get("signal_components")
        normalized.append(
            {
                "agent_type": signal["agent_type"],
                "value": str(signal["value"]),
                "direction": signal["direction"],
                "magnitude": str(signal["magnitude"]),
                "confidence": str(signal["confidence"]),
                "signal_components": components if components is not None else {},
            }
        )
    normalized.sort(key=lambda item: item["agent_type"])
    return {
        "commodity_id": commodity_id,
        "as_of_date": as_of_date.isoformat(),
        "registry_id": str(registry_id),
        "signals": normalized,
    }


def compute_snapshot_hash(
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    signals: list[dict[str, Any]],
) -> str:
    """Deterministic SHA-256 over canonical JSON (stable key ordering)."""
    payload = signal_hash_payload(
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry_id=registry_id,
        signals=signals,
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
