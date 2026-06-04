"""E-01-S10: CommodityRegistry validation and activation tests."""

from __future__ import annotations

from datetime import date
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.services.registry_service import (
    RegistryNotFoundError,
    RegistryService,
)
from backend.app.persistence.validation.registry import (
    RegistryValidationError,
    validate_required_agents,
)


def _decision_rules() -> dict:
    return {
        "msp_proximity_pct": 0.03,
        "default_partial_sell_pct": 0.50,
        "formula_version": "v1.0.0",
    }


def _registry_row(
    *,
    commodity_id: str = "cotton_test",
    version: str = "1.0.0",
    is_active: bool = False,
) -> CommodityRegistryModel:
    return CommodityRegistryModel(
        registry_id=uuid4(),
        commodity_id=commodity_id,
        version=version,
        effective_from=date(2026, 1, 1),
        is_active=is_active,
        required_agents=["Market", "Futures"],
        optional_agents=["Weather", "Policy", "Demand", "Global"],
        signal_weights={
            "Futures": 0.25,
            "Market": 0.22,
            "Policy": 0.15,
            "Demand": 0.15,
            "Weather": 0.13,
            "Global": 0.10,
        },
        regime_priority=[
            "DATA_DEGRADED",
            "MSP_FLOOR",
            "CURVE_BACKWARDATION",
            "TIGHT_SUPPLY",
            "EXPORT_PUSH",
            "NORMAL",
        ],
        forecast_horizons=[30, 60, 90],
        decision_rules=_decision_rules(),
    )


def test_required_agents_json_schema_rejects_empty() -> None:
    with pytest.raises(RegistryValidationError, match="must not be empty"):
        validate_required_agents([])


def test_required_agents_json_schema_rejects_invalid_agent() -> None:
    with pytest.raises(RegistryValidationError, match="invalid agent type"):
        validate_required_agents(["NotAnAgent"])


@pytest.mark.integration
def test_single_active_registry(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id="reg_active_test",
            name="Registry Active Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()

        repo = CommodityRegistryRepository(session)
        first = _registry_row(commodity_id="reg_active_test", version="1.0.0")
        first.is_active = True
        repo.insert_version(first)

        second = _registry_row(commodity_id="reg_active_test", version="1.1.0")
        second.is_active = True
        session.add(second)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.delete(session.get(CommodityModel, "reg_active_test"))
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_version_activation(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id="reg_activate_test",
            name="Registry Activate Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()

        repo = CommodityRegistryRepository(session)
        v1 = _registry_row(commodity_id="reg_activate_test", version="1.0.0")
        repo.insert_version(v1)
        repo.activate_version(v1.registry_id, effective_to_for_prior=date(2026, 6, 3))

        v2 = _registry_row(commodity_id="reg_activate_test", version="1.1.0")
        repo.insert_version(v2)
        repo.activate_version(v2.registry_id, effective_to_for_prior=date(2026, 6, 3))
        session.commit()

        service = RegistryService(session)
        active = service.get_active_config("reg_activate_test")
        assert active.version == "1.1.0"
        assert active.is_active is True

        prior = session.get(CommodityRegistryModel, v1.registry_id)
        assert prior is not None
        assert prior.is_active is False
        assert prior.effective_to == date(2026, 6, 3)

        session.delete(prior)
        session.delete(active)
        session.delete(commodity)
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_registry_service_raises_when_no_active(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id="reg_missing_test",
            name="Registry Missing Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.commit()

        service = RegistryService(session)
        with pytest.raises(RegistryNotFoundError):
            service.get_active_config("reg_missing_test")

        session.delete(commodity)
        session.commit()
    engine.dispose()
