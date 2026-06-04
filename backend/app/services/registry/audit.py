"""Registry activation audit events — TDS-012 §6 hook (E-02-S02)."""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from shared.domain.enums import EventType

_log = logging.getLogger(__name__)


def config_diff_hash(config: dict[str, Any]) -> str:
    """Stable SHA-256 hash of normalized registry config for audit trail."""
    normalized = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def emit_registry_version_activated(
    *,
    commodity_id: str,
    registry_id: str,
    version: str,
    prior_registry_id: str | None,
    config_snapshot: dict[str, Any],
) -> None:
    """
    Log REGISTRY_VERSION_ACTIVATED for ops audit (E-11 hook placeholder).
    """
    payload = {
        "event_type": EventType.REGISTRY_VERSION_ACTIVATED.value,
        "commodity_id": commodity_id,
        "registry_id": registry_id,
        "version": version,
        "prior_registry_id": prior_registry_id,
        "config_diff_hash": config_diff_hash(config_snapshot),
    }
    _log.info("registry_version_activated", extra=payload)
