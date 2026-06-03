"""E-01-S03: reference entity FK and hierarchy tests."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.persistence.models.reference import (
    CommodityModel,
    CommodityProfileModel,
    CommodityStatus,
    MarketModel,
    RegionModel,
    RegionType,
)

pytestmark = pytest.mark.integration


def test_commodity_profile_fk(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id="cotton_test",
            name="Test Cotton",
            status=CommodityStatus.ACTIVE.value,
        )
        session.add(commodity)
        session.flush()
        profile = CommodityProfileModel(
            commodity_id="cotton_test",
            display_name="Test Cotton",
            unit="quintal",
            currency="INR",
            quality_dimensions=["grade_a"],
            storage_characteristics={"moisture_sensitive": True},
            participant_roles_enabled=[
                "Farmer",
                "Trader",
                "Ginner",
                "Miller",
                "Exporter",
                "Aggregator",
            ],
            phase_1_active_roles=["Farmer", "Trader"],
        )
        session.add(profile)
        session.commit()

        loaded = session.get(CommodityProfileModel, "cotton_test")
        assert loaded is not None
        assert loaded.commodity.commodity_id == "cotton_test"
        session.delete(loaded)
        session.delete(session.get(CommodityModel, "cotton_test"))
        session.commit()
    engine.dispose()


def test_region_market_hierarchy(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id="hier_test",
            name="Hierarchy Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()

        region = RegionModel(
            region_id="reg_hier_1",
            commodity_id="hier_test",
            name="Test State",
            type=RegionType.STATE.value,
        )
        session.add(region)
        session.flush()

        market = MarketModel(
            market_id="mkt_hier_1",
            region_id="reg_hier_1",
            commodity_id="hier_test",
            market_type="mandi",
            name="Test Mandi",
        )
        session.add(market)
        session.commit()

        assert session.get(MarketModel, "mkt_hier_1") is not None

        session.delete(session.get(MarketModel, "mkt_hier_1"))
        session.delete(session.get(RegionModel, "reg_hier_1"))
        session.delete(session.get(CommodityModel, "hier_test"))
        session.commit()
    engine.dispose()


def test_market_requires_valid_region_fk(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id="fk_fail_test",
            name="FK Fail",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()
        bad_market = MarketModel(
            market_id="mkt_bad",
            region_id="nonexistent_region",
            commodity_id="fk_fail_test",
            market_type="mandi",
            name="Bad",
        )
        session.add(bad_market)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        commodity_row = session.get(CommodityModel, "fk_fail_test")
        if commodity_row is not None:
            session.delete(commodity_row)
            session.commit()
    engine.dispose()
