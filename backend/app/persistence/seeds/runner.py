"""Seed runner stub — full cotton seed deferred to E-02."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from sqlalchemy.orm import Session

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture from seeds/fixtures/ (E-02 will add cotton.json)."""
    path = FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        msg = f"Fixture not found: {path} (E-02 adds commodity seed data)"
        raise FileNotFoundError(msg)
    with path.open(encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


class SeedRunner:
    """
    Framework for applying reference seed data inside a transaction.
    E-01 ships structure only; E-02 implements apply() for cotton.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def apply(self, fixture_name: str) -> None:
        """Apply fixture rows — not implemented until E-02."""
        msg = (
            f"Seed apply for '{fixture_name}' is a stub in E-01; "
            "implement in E-02 Commodity Registry epic"
        )
        raise NotImplementedError(msg)
