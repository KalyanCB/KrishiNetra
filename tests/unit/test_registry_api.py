"""E-02-S05/S06: Registry API contract tests."""

from __future__ import annotations

import os
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.seeds.runner import SeedRunner

OPS_KEY = "test-ops-key-e02"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def ops_settings() -> patch:
    return patch(
        "backend.app.api.v1.registry.get_settings",
        return_value=type(
            "S",
            (),
            {"ops_api_key": OPS_KEY},
        )(),
    )


@pytest.mark.integration
def test_get_commodities_contract(migrated_database: str, client: TestClient) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()
    engine.dispose()

    response = client.get("/v1/commodities")
    assert response.status_code == 200
    body = response.json()
    assert "commodities" in body
    cotton = next(c for c in body["commodities"] if c["commodity_id"] == "cotton")
    assert cotton["status"] == "active"
    assert len(cotton["participant_roles_enabled"]) == 6
    assert cotton["phase_1_active_roles"] == ["Farmer", "Trader"]

    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
    engine.dispose()


@pytest.mark.integration
def test_get_active_registry_contract(
    migrated_database: str, client: TestClient
) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()
    engine.dispose()

    response = client.get("/v1/commodities/cotton/registry/active")
    assert response.status_code == 200
    body = response.json()
    assert "Market" in body["required_agents"]
    assert "Futures" in body["required_agents"]
    assert body["version"] == "1.0.0"
    assert body["decision_rules_public"]["msp_proximity_pct"] == 0.03
    assert body["decision_rules_public"]["default_partial_sell_pct"] == 0.5
    assert response.headers.get("Cache-Control") == "public, max-age=300"

    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)
    engine.dispose()


def test_registry_public_anonymous(client: TestClient) -> None:
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL required")
    response = client.get("/v1/commodities/cotton/registry/active")
    assert response.status_code in {200, 404}


def test_internal_registry_requires_api_key(
    client: TestClient, ops_settings: patch
) -> None:
    with ops_settings:
        response = client.post(
            "/v1/internal/registry/versions",
            json={"commodity_id": "cotton", "version": "9.9.9"},
        )
        assert response.status_code == 401


@pytest.mark.integration
def test_activate_registry_swaps_active(
    migrated_database: str, client: TestClient, ops_settings: patch
) -> None:
    commodity_id = f"api_reg_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        session.add(
            CommodityModel(
                commodity_id=commodity_id,
                name="API Registry Test",
                status=CommodityStatus.ACTIVE.value,
            )
        )
        session.commit()

        payload = {
            "commodity_id": commodity_id,
            "version": "2.0.0",
            "effective_from": "2026-06-04",
            "required_agents": ["Market", "Futures"],
            "optional_agents": ["Weather"],
            "signal_weights": {"Market": 0.55, "Futures": 0.35, "Weather": 0.10},
            "forecast_horizons": [30, 60, 90],
            "decision_rules": {
                "msp_proximity_pct": 0.03,
                "default_partial_sell_pct": 0.50,
                "formula_version": "2.0.0",
            },
        }

        with ops_settings:
            create_resp = client.post(
                "/v1/internal/registry/versions",
                json=payload,
                headers={"X-API-Key": OPS_KEY},
            )
            assert create_resp.status_code == 200
            registry_id = create_resp.json()["registry_id"]

            activate_resp = client.post(
                f"/v1/internal/registry/versions/{registry_id}/activate",
                headers={"X-API-Key": OPS_KEY},
            )
            assert activate_resp.status_code == 200
            assert activate_resp.json()["is_active"] is True

        active = session.scalars(
            select(CommodityRegistryModel).where(
                CommodityRegistryModel.commodity_id == commodity_id,
                CommodityRegistryModel.is_active.is_(True),
            )
        ).first()
        assert active is not None
        assert active.version == "2.0.0"

        for row in session.scalars(
            select(CommodityRegistryModel).where(
                CommodityRegistryModel.commodity_id == commodity_id
            )
        ):
            session.delete(row)
        session.delete(session.get(CommodityModel, commodity_id))
        session.commit()
    engine.dispose()


def _cleanup_cotton(session: Session) -> None:
    from sqlalchemy import select

    from backend.app.persistence.models.reference import (
        CommodityProfileModel,
        MarketModel,
        RegionModel,
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
