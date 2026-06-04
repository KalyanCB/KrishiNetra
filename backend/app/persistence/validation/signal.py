"""StructuredSignal and SignalSnapshot validation — TDS-006 §3.8 (E-01-S05, PI9)."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from backend.app.persistence.models.signal import StructuredSignalModel
from shared.domain.enums import AgentType, Direction

# PI9 persisted signal row keys (Track C contract for SignalSnapshot.signals JSONB).
PI9_SIGNAL_TYPE = "signal_type"
PI9_SIGNAL_DIRECTION = "signal_direction"
PI9_SIGNAL_MAGNITUDE = "signal_magnitude"
PI9_SIGNAL_CONFIDENCE = "signal_confidence"
PI9_SIGNAL_INPUTS = "signal_inputs"
PI9_AS_OF_DATE = "as_of_date"
PI9_TRACE_ID = "trace_id"

# TDS-006 / E-01-S05 keys (StructuredSignal columns).
TDS_AGENT_TYPE = "agent_type"
TDS_DIRECTION = "direction"
TDS_MAGNITUDE = "magnitude"
TDS_CONFIDENCE = "confidence"
TDS_SIGNAL_COMPONENTS = "signal_components"


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


def validate_trace_id(trace_id: UUID | None) -> None:
    if trace_id is None:
        raise SignalValidationError("trace_id is required for SignalSnapshot persistence")


def normalize_signal_payload(signal: dict[str, Any]) -> dict[str, Any]:
    """Map TDS-006 or PI9 keys to canonical PI9 persisted row shape."""
    signal_type = signal.get(PI9_SIGNAL_TYPE) or signal.get(TDS_AGENT_TYPE)
    if signal_type is None:
        raise SignalValidationError("signal_type (or agent_type) is required")

    direction = signal.get(PI9_SIGNAL_DIRECTION) or signal.get(TDS_DIRECTION)
    if direction is None:
        raise SignalValidationError("signal_direction (or direction) is required")

    magnitude = signal.get(PI9_SIGNAL_MAGNITUDE, signal.get(TDS_MAGNITUDE))
    confidence = signal.get(PI9_SIGNAL_CONFIDENCE, signal.get(TDS_CONFIDENCE))
    if magnitude is None or confidence is None:
        raise SignalValidationError("signal_magnitude and signal_confidence are required")

    inputs = signal.get(PI9_SIGNAL_INPUTS, signal.get(TDS_SIGNAL_COMPONENTS))
    as_of = signal.get(PI9_AS_OF_DATE)
    if as_of is None:
        raise SignalValidationError("as_of_date is required")

    as_of_str = as_of.isoformat() if isinstance(as_of, date) else str(as_of)

    validate_agent_type(str(signal_type))
    validate_direction(str(direction))
    validate_bounded_decimal(magnitude, field_name="signal_magnitude")
    validate_bounded_decimal(confidence, field_name="signal_confidence")

    return {
        PI9_SIGNAL_TYPE: str(signal_type),
        PI9_SIGNAL_DIRECTION: str(direction),
        PI9_SIGNAL_MAGNITUDE: str(magnitude),
        PI9_SIGNAL_CONFIDENCE: str(confidence),
        PI9_SIGNAL_INPUTS: inputs if inputs is not None else {},
        PI9_AS_OF_DATE: as_of_str,
    }


def build_snapshot_signals(
    signal_payloads: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Normalize and sort PI9 contract rows for snapshot JSONB storage."""
    normalized = [normalize_signal_payload(payload) for payload in signal_payloads]
    normalized.sort(key=lambda row: row[PI9_SIGNAL_TYPE])
    return normalized


def structured_signal_to_persisted_row(
    entity: StructuredSignalModel,
) -> dict[str, Any]:
    """Project ORM StructuredSignal to PI9 persisted row."""
    return normalize_signal_payload(
        {
            TDS_AGENT_TYPE: entity.agent_type,
            TDS_DIRECTION: entity.direction,
            TDS_MAGNITUDE: entity.magnitude,
            TDS_CONFIDENCE: entity.confidence,
            TDS_SIGNAL_COMPONENTS: entity.signal_components,
            PI9_AS_OF_DATE: entity.as_of_date,
        }
    )


def signal_hash_payload(
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    signals: list[dict[str, Any]],
    trace_id: UUID | None = None,
) -> dict[str, Any]:
    """Build canonical dict for snapshot_hash (REQ-103 prep)."""
    pi9_rows = build_snapshot_signals(signals)
    payload: dict[str, Any] = {
        "commodity_id": commodity_id,
        "as_of_date": as_of_date.isoformat(),
        "registry_id": str(registry_id),
        "signals": pi9_rows,
    }
    if trace_id is not None:
        payload[PI9_TRACE_ID] = str(trace_id)
    return payload


def compute_snapshot_hash(
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    signals: list[dict[str, Any]],
    trace_id: UUID | None = None,
) -> str:
    """Deterministic SHA-256 over canonical JSON (stable key ordering)."""
    payload = signal_hash_payload(
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry_id=registry_id,
        signals=signals,
        trace_id=trace_id,
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
