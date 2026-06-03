"""E-01-S03: seed framework stub (no cotton data)."""

from __future__ import annotations

import pytest

from backend.app.persistence.seeds.runner import SeedRunner, load_fixture


def test_load_fixture_missing_raises() -> None:
    with pytest.raises(FileNotFoundError, match="E-02"):
        load_fixture("cotton")


def test_seed_runner_apply_not_implemented() -> None:
    from unittest.mock import MagicMock

    from sqlalchemy.orm import Session

    session = MagicMock(spec=Session)
    runner = SeedRunner(session)
    with pytest.raises(NotImplementedError, match="E-02"):
        runner.apply("cotton")
