"""E-01-S11 AC-3: Replay hash input contract (TDS-006 §5)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tests.fixtures.data_foundation import (
    COTTON_TEST_AS_OF,
    COTTON_TEST_FORMULA_VERSION,
    cleanup_cotton_test,
    seed_full_fk_graph,
)

from backend.app.persistence.replay import (
    REPLAY_HASH_INPUT_KEYS,
    build_replay_hash_inputs,
    end_of_as_of_date,
)

pytestmark = pytest.mark.integration


def test_replay_hash_inputs_documented_keys() -> None:
    """AC-3: Replay hash uses registry_id + snapshot_hash + formula_version (E01 §7.3)."""
    assert REPLAY_HASH_INPUT_KEYS == (
        "registry_id",
        "snapshot_hash",
        "formula_version",
    )


def test_replay_hash_inputs_from_fixture(migrated_database: str) -> None:
    """Replay inputs align with ``cotton_test`` S11 fixture graph."""
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        cleanup_cotton_test(session)
        graph = seed_full_fk_graph(session)
        session.commit()

        inputs = build_replay_hash_inputs(
            registry_id=graph.registry.registry_id,
            snapshot_hash=graph.snapshot.snapshot_hash,
            formula_version=graph.recommendation_version.formula_version,
        )
        assert set(inputs) == set(REPLAY_HASH_INPUT_KEYS)
        assert inputs["formula_version"] == COTTON_TEST_FORMULA_VERSION
        assert inputs["snapshot_hash"] == graph.snapshot.snapshot_hash
        assert inputs["registry_id"] == str(graph.registry.registry_id)

        cleanup_cotton_test(session)
    engine.dispose()


def test_end_of_as_of_date_is_utc_inclusive() -> None:
    """Cutoff boundary is end-of-day UTC for historical replay step 2."""
    cutoff = end_of_as_of_date(COTTON_TEST_AS_OF)
    assert cutoff.tzinfo is not None
    assert cutoff.hour == 23
    assert cutoff.date() == COTTON_TEST_AS_OF
