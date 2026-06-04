"""E-01-S10 + E-02: CommodityRegistry validation, activation, and service tests."""

from __future__ import annotations

from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from tests.integration.test_cotton_registry import _cleanup_cotton

from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.seeds.runner import SeedRunner
from backend.app.persistence.validation.registry import (
    RegistryValidationError,
    validate_required_agents,
)
from backend.app.services.registry.service import (
    RegistryNotFoundError,
    RegistryService,
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
    commodity_id = f"reg_active_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id=commodity_id,
            name="Registry Active Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()

        repo = CommodityRegistryRepository(session)
        first = _registry_row(commodity_id=commodity_id, version="1.0.0")
        first.is_active = True
        repo.insert_version(first)
        session.commit()

        second = _registry_row(commodity_id=commodity_id, version="1.1.0")
        second.is_active = True
        session.add(second)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.delete(first)
        session.delete(commodity)
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_version_activation(migrated_database: str) -> None:
    commodity_id = f"reg_activate_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id=commodity_id,
            name="Registry Activate Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()

        repo = CommodityRegistryRepository(session)
        v1 = _registry_row(commodity_id=commodity_id, version="1.0.0")
        repo.insert_version(v1)
        repo.activate_version(v1.registry_id, effective_to_for_prior=date(2026, 6, 3))
        session.commit()

        v2 = _registry_row(commodity_id=commodity_id, version="1.1.0")
        repo.insert_version(v2)
        repo.activate_version(v2.registry_id, effective_to_for_prior=date(2026, 6, 3))
        session.commit()

        active = repo.get_active(commodity_id)
        assert active is not None
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
    RegistryService._cache.clear()
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _cleanup_cotton(session)

        service = RegistryService(session)
        with pytest.raises(RegistryNotFoundError):
            service.get_active_config("cotton")
    engine.dispose()


def _registry_config(row: CommodityRegistryModel) -> dict:
    return {
        "version": row.version,
        "effective_from": row.effective_from,
        "required_agents": row.required_agents,
        "optional_agents": row.optional_agents,
        "signal_weights": row.signal_weights,
        "regime_priority": row.regime_priority,
        "forecast_horizons": row.forecast_horizons,
        "decision_rules": row.decision_rules,
    }


@pytest.mark.integration
def test_historical_registry_readable(migrated_database: str) -> None:
    commodity_id = f"reg_hist_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        session.add(
            CommodityModel(
                commodity_id=commodity_id,
                name="Historical Test",
                status=CommodityStatus.DRAFT.value,
            )
        )
        session.flush()

        service = RegistryService(session)
        v1 = _registry_row(commodity_id=commodity_id, version="1.0.0")
        created_v1 = service.create_registry_version(commodity_id, _registry_config(v1))
        service.activate_registry_version(
            created_v1.registry_id, effective_to_for_prior=date(2026, 6, 3)
        )

        v2 = _registry_row(commodity_id=commodity_id, version="1.1.0")
        created_v2 = service.create_registry_version(commodity_id, _registry_config(v2))
        service.activate_registry_version(
            created_v2.registry_id, effective_to_for_prior=date(2026, 6, 4)
        )
        session.commit()

        historical = service.get_registry_by_id(created_v1.registry_id)
        assert historical is not None
        assert historical.version == "1.0.0"
        assert historical.is_active is False

        for row in session.scalars(
            select(CommodityRegistryModel).where(
                CommodityRegistryModel.commodity_id == commodity_id
            )
        ):
            session.delete(row)
        session.delete(session.get(CommodityModel, commodity_id))
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_activation_audit_log(migrated_database: str) -> None:
    commodity_id = f"reg_audit_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        session.add(
            CommodityModel(
                commodity_id=commodity_id,
                name="Audit Test",
                status=CommodityStatus.DRAFT.value,
            )
        )
        session.flush()

        service = RegistryService(session)
        row = _registry_row(commodity_id=commodity_id)
        created = service.create_registry_version(commodity_id, _registry_config(row))

        with patch(
            "backend.app.services.registry.service.emit_registry_version_activated"
        ) as mock_audit:
            service.activate_registry_version(created.registry_id)
            session.commit()
            mock_audit.assert_called_once()
            assert mock_audit.call_args.kwargs["commodity_id"] == commodity_id

        for row_db in session.scalars(
            select(CommodityRegistryModel).where(
                CommodityRegistryModel.commodity_id == commodity_id
            )
        ):
            session.delete(row_db)
        session.delete(session.get(CommodityModel, commodity_id))
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_registry_cache_invalidation(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    RegistryService._cache.clear()
    with Session(engine) as session:
        _cleanup_cotton(session)
        SeedRunner(session).apply("cotton")
        session.commit()

        service = RegistryService(session)
        first = service.get_active_config("cotton")
        assert first.version == "1.0.0"

        v2_config = _registry_config(
            _registry_row(commodity_id="cotton", version="1.1.0")
        )
        v2_config["effective_from"] = date(2026, 6, 5)
        created = service.create_registry_version("cotton", v2_config)
        service.activate_registry_version(created.registry_id)
        session.commit()

        refreshed = service.get_active_config("cotton")
        assert refreshed.version == "1.1.0"

        RegistryService._cache.clear()
        _cleanup_cotton(session)
    engine.dispose()
