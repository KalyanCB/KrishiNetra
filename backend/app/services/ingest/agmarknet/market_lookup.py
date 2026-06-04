"""Resolve OGD state/district/market triples to E-02 market_id."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class AgmarknetMarketKey:
    """Canonical OGD location key for market resolution."""

    state: str
    district: str
    market: str

    @classmethod
    def from_record_fields(
        cls, *, state: str, district: str, market: str
    ) -> AgmarknetMarketKey:
        return cls(
            state=_normalize(state),
            district=_normalize(district),
            market=_normalize(market),
        )


class AgmarknetMarketLookup:
    """In-memory index of cotton seed markets by Agmarknet identifiers."""

    def __init__(self, entries: dict[AgmarknetMarketKey, str]) -> None:
        self._entries = entries

    def resolve(self, *, state: str, district: str, market: str) -> str | None:
        key = AgmarknetMarketKey.from_record_fields(
            state=state, district=district, market=market
        )
        return self._entries.get(key)

    @classmethod
    def from_markets_seed(cls, markets: list[dict[str, Any]]) -> AgmarknetMarketLookup:
        entries: dict[AgmarknetMarketKey, str] = {}
        for market in markets:
            market_id = market.get("market_id")
            identifiers = market.get("source_identifiers") or {}
            agmarknet = identifiers.get("agmarknet")
            if not market_id or not isinstance(agmarknet, dict):
                continue
            key = AgmarknetMarketKey.from_record_fields(
                state=str(agmarknet["state"]),
                district=str(agmarknet["district"]),
                market=str(agmarknet["market"]),
            )
            entries[key] = str(market_id)
        return cls(entries)


def _normalize(value: str) -> str:
    return value.strip()


def load_market_lookup_from_seed(
    seed_path: Path | None = None,
) -> AgmarknetMarketLookup:
    """Build lookup from cotton.json E-02 seed (Agmarknet markets)."""
    if seed_path is None:
        seed_path = (
            Path(__file__).resolve().parents[3]
            / "persistence"
            / "seeds"
            / "fixtures"
            / "cotton.json"
        )
    data = json.loads(seed_path.read_text(encoding="utf-8"))
    return AgmarknetMarketLookup.from_markets_seed(data.get("markets", []))
