"""PI7 Track B: cotton seed market coverage and Agmarknet lookup."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.app.persistence.seeds.runner import load_fixture
from backend.app.services.ingest.agmarknet.backfill import FixtureReplayOgdClient
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_expected_market_ids,
)
from backend.app.services.ingest.agmarknet.mapper import AgmarknetMapper
from backend.app.services.ingest.agmarknet.market_lookup import (
    AgmarknetMarketKey,
    AgmarknetMarketLookup,
    load_market_lookup_from_seed,
)
from backend.app.services.ingest.agmarknet.parser import parse_ogd_response

_MIN_COTTON_MARKETS = 20
_MARKET_ID_PATTERN = re.compile(r"^mkt_[a-z]{2}_[a-z0-9_]+$")


def _agmarknet_markets(fixture: dict) -> list[dict]:
    return [
        m
        for m in fixture.get("markets", [])
        if (m.get("source_identifiers") or {}).get("agmarknet")
    ]


def test_cotton_seed_has_at_least_twenty_agmarknet_markets() -> None:
    markets = _agmarknet_markets(load_fixture("cotton"))
    assert len(markets) >= _MIN_COTTON_MARKETS


def test_load_expected_market_ids_matches_seed_agmarknet_markets() -> None:
    fixture = load_fixture("cotton")
    seed_ids = {m["market_id"] for m in _agmarknet_markets(fixture)}
    assert set(load_expected_market_ids()) == seed_ids


def test_agmarknet_lookup_keys_are_unique() -> None:
    lookup = load_market_lookup_from_seed()
    keys = list(lookup._entries.keys())
    assert len(keys) == len(set(keys))


@pytest.mark.parametrize(
    ("state", "district", "market", "market_id"),
    [
        ("Telangana", "Khammam", "Khammam", "mkt_tg_khammam_apmc"),
        ("Telangana", "Khammam", "Kesamudram", "mkt_tg_kesamudram"),
        ("Maharashtra", "Amravati", "Amravati", "mkt_mh_amravati"),
        ("Gujarat", "Rajkot", "Rajkot", "mkt_gj_rajkot"),
        ("Andhra Pradesh", "Guntur", "Guntur", "mkt_ap_guntur"),
        ("Andhra Pradesh", "Kurnool", "Adoni", "mkt_ap_adoni"),
        ("Karnataka", "Raichur", "Raichur", "mkt_ka_raichur"),
    ],
)
def test_market_lookup_resolves_belt_mandis(
    state: str, district: str, market: str, market_id: str
) -> None:
    lookup = load_market_lookup_from_seed()
    assert lookup.resolve(state=state, district=district, market=market) == market_id


def test_market_lookup_resolves_all_seed_tuples() -> None:
    fixture = load_fixture("cotton")
    lookup = load_market_lookup_from_seed()
    for market in _agmarknet_markets(fixture):
        ag = market["source_identifiers"]["agmarknet"]
        resolved = lookup.resolve(
            state=ag["state"],
            district=ag["district"],
            market=ag["market"],
        )
        assert resolved == market["market_id"], ag


def test_market_lookup_normalizes_whitespace() -> None:
    lookup = load_market_lookup_from_seed()
    assert (
        lookup.resolve(
            state="  Telangana ",
            district=" Warangal ",
            market="Warangal ",
        )
        == "mkt_tg_warangal"
    )


def test_market_id_convention() -> None:
    for market in _agmarknet_markets(load_fixture("cotton")):
        market_id = market["market_id"]
        assert _MARKET_ID_PATTERN.match(market_id), market_id


def test_from_markets_seed_builds_lookup() -> None:
    markets = _agmarknet_markets(load_fixture("cotton"))
    lookup = AgmarknetMarketLookup.from_markets_seed(markets)
    key = AgmarknetMarketKey.from_record_fields(
        state="Maharashtra", district="Yavatmal", market="Yavatmal"
    )
    assert lookup._entries[key] == "mkt_mh_yavatmal"


def test_belt_fixture_maps_twelve_plus_distinct_market_ids() -> None:
    belt_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "agmarknet"
        / "ogd_cotton_belt_sample.json"
    )
    client = FixtureReplayOgdClient(belt_path)
    raw = client.fetch_all(filters={"arrival_date": "04/06/2026"})
    records = parse_ogd_response({"records": raw})
    mapper = AgmarknetMapper(load_market_lookup_from_seed())
    market_ids: set[str] = set()
    for record in records:
        prices, _ = mapper.map_record(record)
        for price in prices:
            market_ids.add(price.market_id)
    assert len(market_ids) >= 12
