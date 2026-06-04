"""E-01-S11: Replay helper unit tests (no DB)."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

from backend.app.persistence.replay import (
    REPLAY_HASH_INPUT_KEYS,
    build_replay_hash_inputs,
    end_of_as_of_date,
)


def test_build_replay_hash_inputs_returns_documented_keys() -> None:
    registry_id = uuid4()
    inputs = build_replay_hash_inputs(
        registry_id=registry_id,
        snapshot_hash="hash_v1",
        formula_version="v1.0.0",
    )
    assert tuple(inputs.keys()) == REPLAY_HASH_INPUT_KEYS
    assert inputs["registry_id"] == str(registry_id)


def test_end_of_as_of_date_utc_boundary() -> None:
    cutoff = end_of_as_of_date(date(2026, 6, 4))
    assert cutoff.tzinfo is not None
    assert cutoff.date() == date(2026, 6, 4)
