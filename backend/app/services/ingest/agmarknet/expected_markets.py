"""Expected cotton mandi ids for Agmarknet coverage metrics."""

from __future__ import annotations

import json
from pathlib import Path

_COTTON_SEED_PATH = (
    Path(__file__).resolve().parents[3]
    / "persistence"
    / "seeds"
    / "fixtures"
    / "cotton.json"
)


def load_expected_market_ids(seed_path: Path | None = None) -> tuple[str, ...]:
    """E-02 cotton seed mandis with Agmarknet source_identifiers (4 Telangana)."""
    path = seed_path or _COTTON_SEED_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    ids: list[str] = []
    for market in data.get("markets", []):
        market_id = market.get("market_id")
        identifiers = market.get("source_identifiers") or {}
        if market_id and identifiers.get("agmarknet"):
            ids.append(str(market_id))
    return tuple(ids)
