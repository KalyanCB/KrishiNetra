"""E-02-S04/S07: Cotton registry seed and service integration tests."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.persistence.models.reference import (
    CommodityModel,
    CommodityProfileModel,
    CommodityStatus,
    MarketModel,
    RegionModel,
)
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.seeds.runner import SeedRunner, load_fixture
from backend.app.services.registry.mi_stub import load_required_agents
from backend.app.services.registry.service import RegistryNotFoundError, RegistryService

pytestmark = pytest.mark.integration


def _cleanup_cotton(session: Session) -> None:
    from sqlalchemy import text

    session.execute(
        text("DELETE FROM data_quality_snapshot WHERE commodity_id = 'cotton'")
    )
    session.execute(
        text("DELETE FROM price_observation WHERE commodity_id = 'cotton'")
    )
    session.execute(
        text("DELETE FROM arrival_observation WHERE commodity_id = 'cotton'")
    )
    session.execute(
        text("DELETE FROM weather_observation WHERE commodity_id = 'cotton'")
    )
    session.execute(
        text(
            """
            DELETE FROM weather_observation
            WHERE region_id IN (
                SELECT region_id FROM region WHERE commodity_id = 'cotton'
            )
            """
        )
    )
    session.execute(
        text("DELETE FROM structured_signal WHERE commodity_id = 'cotton'")
    )
    session.execute(
        text("DELETE FROM signal_snapshot WHERE commodity_id = 'cotton'")
    )
    for market in session.scalars(
        select(MarketModel).where(MarketModel.commodity_id == "cotton")
    ):
        session.delete(market)
    for region in session.scalars(
        select(RegionModel).where(RegionModel.commodity_id == "cotton")
    ):
        session.delete(region)
    for registry in session.scalars(
        select(CommodityRegistryModel).where(
            CommodityRegistryModel.commodity_id == "cotton"
        )
    ):
        session.delete(registry)
    profile = session.get(CommodityProfileModel, "cotton")
    if profile is not None:
        session.delete(profile)
    commodity = session.get(CommodityModel, "cotton")
    if commodity is not None:
        session.delete(commodity)
    session.commit()


def test_cotton_commodity_active(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()

        commodity = session.get(CommodityModel, "cotton")
        assert commodity is not None
        assert commodity.status == CommodityStatus.ACTIVE.value
        assert commodity.reference_implementation_flag is True

        _cleanup_cotton(session)
    engine.dispose()


def test_participant_roles_six(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()

        profile = session.get(CommodityProfileModel, "cotton")
        assert profile is not None
        assert len(profile.participant_roles_enabled or []) == 6

        _cleanup_cotton(session)
    engine.dispose()


def test_phase_1_active_subset(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()

        profile = session.get(CommodityProfileModel, "cotton")
        assert profile is not None
        enabled = set(profile.participant_roles_enabled or [])
        phase_1 = set(profile.phase_1_active_roles or [])
        assert phase_1 <= enabled

        _cleanup_cotton(session)
    engine.dispose()


def test_cotton_seed_active_registry(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()

        service = RegistryService(session)
        active = service.get_active_config("cotton")
        fixture = load_fixture("cotton")["registry"]

        assert active.version == "1.0.0"
        assert active.is_active is True
        assert active.required_agents == fixture["required_agents"]
        assert active.optional_agents == fixture["optional_agents"]
        assert active.signal_weights == fixture["signal_weights"]
        assert active.regime_priority == fixture["regime_priority"]
        assert "acreage" in (active.weather_variables or [])

        _cleanup_cotton(session)
    engine.dispose()


def test_registry_fixture_snapshot(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()

        active = RegistryService(session).get_active_config("cotton")
        normalized = {
            "required_agents": active.required_agents,
            "optional_agents": active.optional_agents,
            "signal_weights": active.signal_weights,
            "regime_priority": active.regime_priority,
            "decision_rules": active.decision_rules,
        }
        digest = hashlib.sha256(
            json.dumps(normalized, sort_keys=True).encode()
        ).hexdigest()
        assert len(digest) == 64

        _cleanup_cotton(session)
    engine.dispose()


def test_seed_idempotent(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()
        count_after_first = session.scalar(
            select(func.count())
            .select_from(CommodityRegistryModel)
            .where(CommodityRegistryModel.commodity_id == "cotton")
        )

        SeedRunner(session).apply("cotton")
        session.commit()
        count_after_second = session.scalar(
            select(func.count())
            .select_from(CommodityRegistryModel)
            .where(CommodityRegistryModel.commodity_id == "cotton")
        )
        assert count_after_first == count_after_second == 1

        _cleanup_cotton(session)
    engine.dispose()


def test_region_market_hierarchy_telangana(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()

        state = session.get(RegionModel, "reg_tg_state")
        assert state is not None
        assert state.type == "state"

        khammam = session.get(MarketModel, "mkt_tg_khammam_apmc")
        assert khammam is not None
        assert khammam.commodity_id == "cotton"
        assert khammam.region_id == "reg_tg_khammam"

        _cleanup_cotton(session)
    engine.dispose()


def test_registry_service_cotton(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()

        agents = load_required_agents(session, "cotton")
        assert "Market" in agents
        assert "Futures" in agents

        _cleanup_cotton(session)
    engine.dispose()


def test_registry_service_non_cotton_raises(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity_id = f"other_{uuid4().hex[:8]}"
        session.add(
            CommodityModel(
                commodity_id=commodity_id,
                name="Other",
                status=CommodityStatus.ACTIVE.value,
            )
        )
        session.commit()

        service = RegistryService(session)
        with pytest.raises(RegistryNotFoundError):
            service.get_active_config(commodity_id)

        session.delete(session.get(CommodityModel, commodity_id))
        session.commit()
    engine.dispose()
