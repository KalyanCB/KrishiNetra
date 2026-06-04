"""Agmarknet parser and mapper unit tests (PI5 spike + E-03-S01 shared)."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    ObservationValidationStatus,
    PriceObservationModel,
)
from backend.app.persistence.repositories.observation import (
    ArrivalObservationRepository,
    PriceObservationRepository,
)
from backend.app.services.ingest.agmarknet.constants import SOURCE_AGMARKNET
from backend.app.services.ingest.agmarknet.mapper import (
    AgmarknetMapper,
    resolve_commodity_id,
)
from backend.app.services.ingest.agmarknet.market_lookup import (
    load_market_lookup_from_seed,
)
from backend.app.services.ingest.agmarknet.parser import (
    AgmarknetParseError,
    parse_arrival_date,
    parse_ogd_response,
    parse_record,
)

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "agmarknet"
    / "ogd_telangana_sample.json"
)


@pytest.fixture
def ogd_payload() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def market_lookup():
    return load_market_lookup_from_seed()


@pytest.fixture
def mapper(market_lookup) -> AgmarknetMapper:
    return AgmarknetMapper(market_lookup)


def test_parse_arrival_date_dd_mm_yyyy() -> None:
    assert parse_arrival_date("26/03/2022") == date(2022, 3, 26)
    assert parse_arrival_date("04/06/2026") == date(2026, 6, 4)


def test_parse_arrival_date_rejects_invalid() -> None:
    with pytest.raises(AgmarknetParseError, match="DD/MM/YYYY"):
        parse_arrival_date("2022-03-26")


def test_parse_record_khammam_cotton() -> None:
    row = {
        "state": "Telangana",
        "district": "Khammam",
        "market": "Khammam",
        "commodity": "Cotton",
        "variety": "Cotton",
        "grade": "FAQ",
        "arrival_date": "26/03/2022",
        "min_price": 9000,
        "max_price": 12001,
        "modal_price": 10500,
    }
    record = parse_record(row)
    assert record.modal_price == Decimal("10500")
    assert record.arrival_date == date(2022, 3, 26)


def test_parse_ogd_response_envelope(ogd_payload: dict) -> None:
    records = parse_ogd_response(ogd_payload)
    assert len(records) == 4


def test_resolve_commodity_cotton_variants() -> None:
    assert resolve_commodity_id("Cotton") == "cotton"
    assert resolve_commodity_id("Kapas") == "cotton"
    assert resolve_commodity_id("Cotton (Unginned)") == "cotton"
    assert resolve_commodity_id("Cotton Seed") is None
    assert resolve_commodity_id("Maize") is None


def test_market_lookup_resolves_telangana_proof_mandis(market_lookup) -> None:
    assert (
        market_lookup.resolve(state="Telangana", district="Khammam", market="Khammam")
        == "mkt_tg_khammam_apmc"
    )
    assert (
        market_lookup.resolve(state="Telangana", district="Warangal", market="Warangal")
        == "mkt_tg_warangal"
    )
    assert (
        market_lookup.resolve(
            state="Telangana", district="Karimnagar", market="Karimnagar"
        )
        == "mkt_tg_karimnagar"
    )
    assert (
        market_lookup.resolve(
            state="Telangana", district="Khammam", market="Kesamudram"
        )
        == "mkt_tg_kesamudram"
    )


def test_mapper_khammam_cotton_modal_price(mapper) -> None:
    records = parse_ogd_response(
        {
            "records": [
                {
                    "state": "Telangana",
                    "district": "Khammam",
                    "market": "Khammam",
                    "commodity": "Cotton",
                    "variety": "Cotton",
                    "grade": "FAQ",
                    "arrival_date": "26/03/2022",
                    "modal_price": 10500,
                    "min_price": 9000,
                    "max_price": 12001,
                }
            ]
        }
    )
    prices, arrival = mapper.map_record(records[0])
    assert arrival is None
    assert len(prices) == 3
    modal = next(p for p in prices if p.price_type == "modal")
    assert modal.market_id == "mkt_tg_khammam_apmc"
    assert modal.commodity_id == "cotton"
    assert modal.value == Decimal("10500")
    assert modal.unit == "quintal"
    assert modal.currency == "INR"
    assert modal.as_of_date == date(2022, 3, 26)
    assert modal.source == SOURCE_AGMARKNET
    assert modal.quality_grade == "Cotton|FAQ"


def test_mapper_khammam_arrival_tonnes_to_quintals(mapper) -> None:
    records = parse_ogd_response(
        {
            "records": [
                {
                    "state": "Telangana",
                    "district": "Khammam",
                    "market": "Khammam",
                    "commodity": "Cotton",
                    "arrival_tonnes": 42.5,
                    "arrival_date": "26/03/2022",
                }
            ]
        }
    )
    _, arrival = mapper.map_record(records[0])
    assert arrival is not None
    assert arrival.volume == Decimal("425")
    assert arrival.unit == "quintal"
    assert arrival.market_id == "mkt_tg_khammam_apmc"


def test_mapper_drops_non_cotton_and_unknown_market(mapper, ogd_payload: dict) -> None:
    records = parse_ogd_response(ogd_payload)
    prices, arrivals = mapper.map_records(records)
    market_ids = {p.market_id for p in prices}
    assert "mkt_tg_khammam_apmc" in market_ids
    assert "mkt_tg_warangal" in market_ids
    assert all(p.commodity_id == "cotton" for p in prices)
    assert not any(p.market_id == "mkt_tg_dharmapuri" for p in prices)
    assert len(arrivals) == 1
    assert arrivals[0].volume == Decimal("425")


def test_mapper_kapas_maps_to_cotton(mapper) -> None:
    records = parse_ogd_response(
        {
            "records": [
                {
                    "state": "Telangana",
                    "district": "Warangal",
                    "market": "Warangal",
                    "commodity": "Kapas",
                    "arrival_date": "04/06/2026",
                    "modal_price": 10000,
                }
            ]
        }
    )
    prices, _ = mapper.map_record(records[0])
    assert len(prices) == 1
    assert prices[0].market_id == "mkt_tg_warangal"


def test_parse_ogd_response_missing_records_raises() -> None:
    with pytest.raises(AgmarknetParseError, match="records"):
        parse_ogd_response({})


@pytest.mark.integration
def test_agmarknet_drafts_persist_after_cotton_seed(migrated_database: str) -> None:
    """Optional: insert mapped drafts when DATABASE_URL points at migrated DB."""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from tests.integration.test_cotton_registry import _cleanup_cotton

    from backend.app.persistence.seeds.runner import SeedRunner

    engine = create_engine(migrated_database, pool_pre_ping=True)
    lookup = load_market_lookup_from_seed()
    mapper = AgmarknetMapper(lookup)
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    records = parse_ogd_response(payload)
    prices, arrivals = mapper.map_records(records)
    khammam_prices = [p for p in prices if p.market_id == "mkt_tg_khammam_apmc"]
    observed = datetime(2022, 3, 26, 18, 30, tzinfo=UTC)

    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()

    try:
        with Session(engine) as session:
            price_repo = PriceObservationRepository(session)
            arrival_repo = ArrivalObservationRepository(session)
            for draft in khammam_prices:
                price_repo.insert_observation(
                    PriceObservationModel(
                        observation_id=uuid4(),
                        market_id=draft.market_id,
                        commodity_id=draft.commodity_id,
                        price_type=draft.price_type,
                        value=draft.value,
                        unit=draft.unit,
                        currency=draft.currency,
                        observed_at=observed,
                        as_of_date=draft.as_of_date,
                        source=draft.source,
                        quality_grade=draft.quality_grade,
                        validation_status=ObservationValidationStatus.RECEIVED.value,
                    )
                )
            for draft in arrivals:
                arrival_repo.insert_observation(
                    ArrivalObservationModel(
                        observation_id=uuid4(),
                        market_id=draft.market_id,
                        commodity_id=draft.commodity_id,
                        volume=draft.volume,
                        unit=draft.unit,
                        observed_at=observed,
                        as_of_date=draft.as_of_date,
                        source=draft.source,
                        validation_status=ObservationValidationStatus.RECEIVED.value,
                    )
                )
            session.commit()
            loaded = price_repo.list_by_commodity_date_range(
                "cotton", date(2022, 3, 26), date(2022, 3, 26)
            )
            assert any(row.price_type == "modal" for row in loaded)
    finally:
        with Session(engine) as session:
            for model in (PriceObservationModel, ArrivalObservationModel):
                for row in session.scalars(
                    select(model).where(
                        model.commodity_id == "cotton",
                        model.as_of_date == date(2022, 3, 26),
                    )
                ):
                    session.delete(row)
            _cleanup_cotton(session)
            session.commit()
    engine.dispose()
