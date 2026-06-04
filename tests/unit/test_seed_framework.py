"""E-01-S03 / E-02: seed framework tests."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from backend.app.persistence.seeds.runner import SeedRunner, load_fixture


def test_load_fixture_cotton() -> None:
    data = load_fixture("cotton")
    assert data["commodity"]["commodity_id"] == "cotton"
    assert data["registry"]["version"] == "1.0.0"


def test_seed_runner_apply_unknown_fixture() -> None:
    session = MagicMock(spec=Session)
    runner = SeedRunner(session)
    with pytest.raises(ValueError, match="Unknown fixture"):
        runner.apply("unknown_fixture")


def test_cotton_fixture_weights_sum_to_one() -> None:
    weights = load_fixture("cotton")["registry"]["signal_weights"]
    assert abs(sum(weights.values()) - 1.0) < 0.001


def test_cotton_fixture_has_telangana_regions() -> None:
    data = load_fixture("cotton")
    region_ids = {r["region_id"] for r in data["regions"]}
    assert "reg_tg_state" in region_ids
    assert len(data["markets"]) >= 4
