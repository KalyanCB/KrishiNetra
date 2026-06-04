"""PI5 Track C: Cotton + Telangana observation population proof (E-03)."""

from __future__ import annotations

import os
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    PriceObservationModel,
)
from backend.app.persistence.models.reference import CommodityModel, MarketModel
from backend.app.spike.agmarknet.population import (
    COTTON_COMMODITY_ID,
    SOURCE_AGMARKNET,
    count_cotton_agmarknet,
    delete_cotton_agmarknet_observations,
    load_fixture_drafts,
    run_population_proof,
)

pytestmark = pytest.mark.integration

TELANGANA_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "agmarknet"
    / "ogd_telangana_sample.json"
)

EXPECTED_DRAFT_PRICES = 7
EXPECTED_DRAFT_ARRIVALS = 1


def test_fixture_maps_cotton_telangana_drafts() -> None:
    ogd_count, prices, arrivals = load_fixture_drafts(TELANGANA_FIXTURE)
    assert ogd_count == 4
    assert len(prices) == EXPECTED_DRAFT_PRICES
    assert len(arrivals) == EXPECTED_DRAFT_ARRIVALS
    assert all(p.commodity_id == COTTON_COMMODITY_ID for p in prices)
    assert {p.market_id for p in prices} == {
        "mkt_tg_khammam_apmc",
        "mkt_tg_warangal",
    }
    assert arrivals[0].market_id == "mkt_tg_khammam_apmc"
    assert arrivals[0].volume == Decimal("425")


def test_observation_population_proof(migrated_database: str) -> None:
    if os.environ.get("KRISHI_PRESERVE_INTEGRATION_CORPUS"):
        pytest.skip("Preserves @5433 observation corpus (PI10 merge gate)")
    engine = create_engine(migrated_database, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            delete_cotton_agmarknet_observations(session)
            before = count_cotton_agmarknet(session)
            assert before.total == 0

            result = run_population_proof(session, fixture_path=TELANGANA_FIXTURE)
            assert result.fk_valid is True
            assert result.inserted.price == EXPECTED_DRAFT_PRICES
            assert result.inserted.arrival == EXPECTED_DRAFT_ARRIVALS
            assert result.after.price == before.price + EXPECTED_DRAFT_PRICES
            assert result.after.arrival == before.arrival + EXPECTED_DRAFT_ARRIVALS

            modal_khammam = session.scalar(
                select(PriceObservationModel.value)
                .where(
                    PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
                    PriceObservationModel.market_id == "mkt_tg_khammam_apmc",
                    PriceObservationModel.price_type == "modal",
                    PriceObservationModel.as_of_date == date(2022, 3, 26),
                )
                .limit(1)
            )
            assert modal_khammam == Decimal("10500")

            arrival_vol = session.scalar(
                select(ArrivalObservationModel.volume).where(
                    ArrivalObservationModel.commodity_id == COTTON_COMMODITY_ID,
                    ArrivalObservationModel.market_id == "mkt_tg_khammam_apmc",
                    ArrivalObservationModel.as_of_date == date(2022, 3, 26),
                )
            )
            assert arrival_vol == Decimal("425")

            assert session.get(CommodityModel, COTTON_COMMODITY_ID) is not None
            for market_id in ("mkt_tg_khammam_apmc", "mkt_tg_warangal"):
                assert session.get(MarketModel, market_id) is not None

            # Append-only: second run adds rows (no business-key dedupe).
            second = run_population_proof(session, fixture_path=TELANGANA_FIXTURE, apply_seed=False)
            assert second.after.price == result.after.price + EXPECTED_DRAFT_PRICES

            agmarknet_price_count = session.scalar(
                select(func.count())
                .select_from(PriceObservationModel)
                .where(
                    PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
                    PriceObservationModel.source == SOURCE_AGMARKNET,
                )
            )
            assert agmarknet_price_count == EXPECTED_DRAFT_PRICES * 2

            delete_cotton_agmarknet_observations(session)
            after_cleanup = count_cotton_agmarknet(session)
            assert after_cleanup.total == 0
    finally:
        engine.dispose()
