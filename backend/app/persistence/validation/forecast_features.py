"""ForecastFeatureSnapshot validation and deterministic feature_hash — PI10 Track C."""

from __future__ import annotations

import hashlib
import json
from datetime import date
from typing import Any
from uuid import UUID

ASSEMBLY_VERSION = "forecast-features-v1.0.0"


class ForecastFeatureValidationError(ValueError):
    """Raised when forecast feature snapshot fields fail validation."""


def validate_trace_id(trace_id: UUID | None) -> None:
    if trace_id is None:
        raise ForecastFeatureValidationError(
            "trace_id is required for ForecastFeatureSnapshot persistence"
        )


def _sorted_feature_values(values: dict[str, Any]) -> dict[str, Any]:
    return {key: values[key] for key in sorted(values)}


def feature_hash_payload(
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    feature_values: dict[str, Any],
    trace_id: UUID | None = None,
) -> dict[str, Any]:
    """Build canonical dict for feature_hash (REQ-103 prep)."""
    payload: dict[str, Any] = {
        "commodity_id": commodity_id,
        "as_of_date": as_of_date.isoformat(),
        "registry_id": str(registry_id),
        "feature_values": _sorted_feature_values(feature_values),
        "assembly_version": ASSEMBLY_VERSION,
    }
    if trace_id is not None:
        payload["trace_id"] = str(trace_id)
    return payload


def compute_feature_hash(
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    feature_values: dict[str, Any],
    trace_id: UUID | None = None,
) -> str:
    """Deterministic SHA-256 over canonical JSON (stable key ordering)."""
    payload = feature_hash_payload(
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry_id=registry_id,
        feature_values=feature_values,
        trace_id=trace_id,
    )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
