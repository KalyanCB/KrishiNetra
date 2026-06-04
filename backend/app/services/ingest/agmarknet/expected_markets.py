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

# PI6 proof window — four Telangana mandis (legacy stats scope).
TELANGANA_PRIMARY_MARKET_IDS: tuple[str, ...] = (
    "mkt_tg_khammam_apmc",
    "mkt_tg_warangal",
    "mkt_tg_karimnagar",
    "mkt_tg_kesamudram",
)


def load_telangana_primary_market_ids() -> tuple[str, ...]:
    """Telangana primary mandis for legacy PI5/PI6 proof coverage scope."""
    return TELANGANA_PRIMARY_MARKET_IDS


def _load_agmarknet_markets(seed_path: Path | None = None) -> list[dict]:
    path = seed_path or _COTTON_SEED_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    return [
        m
        for m in data.get("markets", [])
        if (m.get("source_identifiers") or {}).get("agmarknet")
    ]


def load_expected_market_ids(seed_path: Path | None = None) -> tuple[str, ...]:
    """E-02 cotton seed mandis with Agmarknet source_identifiers (PI7 belt: 27)."""
    return tuple(
        str(m["market_id"])
        for m in _load_agmarknet_markets(seed_path)
        if m.get("market_id")
    )


def load_backfill_ogd_states(seed_path: Path | None = None) -> tuple[str, ...]:
    """Distinct OGD ``state`` filter values for cotton belt historical pulls."""
    states: set[str] = set()
    for market in _load_agmarknet_markets(seed_path):
        ag = (market.get("source_identifiers") or {}).get("agmarknet") or {}
        state = ag.get("state")
        if state:
            states.add(str(state).strip())
    return tuple(sorted(states))
