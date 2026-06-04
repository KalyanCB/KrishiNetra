"""E-01-S08: DataQualitySnapshot validation and persistence tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.repositories.quality import DataQualitySnapshotRepository
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.validation.quality import (
    QualityValidationError,
    validate_quality_score,
)


def _decision_rules() -> dict:
    return {
        "msp_proximity_pct": 0.03,
        "default_partial_sell_pct": 0.50,
        "formula_version": "v1.0.0",
    }


def test_quality_score_bounds_rejects_above_one() -> None:
    with pytest.raises(QualityValidationError, match="\\[0, 1\\]"):
        validate_quality_score(1.01)


def test_quality_score_bounds_accepts_edges() -> None:
    validate_quality_score(0.0)
    validate_quality_score(1.0)


@pytest.mark.integration
def test_quality_snapshot_persistence(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id="quality_test",
            name="Quality Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()

        registry = CommodityRegistryModel(
            registry_id=uuid4(),
            commodity_id="quality_test",
            version="1.0.0",
            effective_from=date(2026, 1, 1),
            is_active=True,
            required_agents=["Market", "Futures"],
            decision_rules=_decision_rules(),
        )
        CommodityRegistryRepository(session).insert_version(registry)

        repo = DataQualitySnapshotRepository(session)
        snapshot = DataQualitySnapshotModel(
            quality_snapshot_id=uuid4(),
            commodity_id="quality_test",
            as_of_date=date(2026, 6, 4),
            registry_id=registry.registry_id,
            source_health={"agmarknet": "fresh", "futures_feed": "fresh"},
            overall_quality_score=Decimal("0.92"),
            agmarknet_lag_hours=Decimal("2.5"),
            futures_feed_ok=True,
            signals_missing=[],
            confidence_penalty_factor=Decimal("0.05"),
        )
        repo.insert_snapshot(snapshot)
        session.commit()

        loaded = repo.get_by_commodity_date(
            "quality_test",
            date(2026, 6, 4),
            registry_id=registry.registry_id,
        )
        assert loaded is not None
        assert loaded.overall_quality_score == Decimal("0.9200")

        session.delete(loaded)
        session.delete(registry)
        session.delete(commodity)
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_quality_snapshot_unique_per_day(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id="quality_unique_test",
            name="Quality Unique Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()

        registry = CommodityRegistryModel(
            registry_id=uuid4(),
            commodity_id="quality_unique_test",
            version="1.0.0",
            effective_from=date(2026, 1, 1),
            is_active=True,
            required_agents=["Market", "Futures"],
            decision_rules=_decision_rules(),
        )
        CommodityRegistryRepository(session).insert_version(registry)

        repo = DataQualitySnapshotRepository(session)
        first = DataQualitySnapshotModel(
            quality_snapshot_id=uuid4(),
            commodity_id="quality_unique_test",
            as_of_date=date(2026, 6, 4),
            registry_id=registry.registry_id,
            source_health={"agmarknet": "fresh"},
            overall_quality_score=Decimal("0.80"),
            futures_feed_ok=True,
        )
        repo.insert_snapshot(first)
        session.flush()

        duplicate = DataQualitySnapshotModel(
            quality_snapshot_id=uuid4(),
            commodity_id="quality_unique_test",
            as_of_date=date(2026, 6, 4),
            registry_id=registry.registry_id,
            source_health={"agmarknet": "stale"},
            overall_quality_score=Decimal("0.70"),
            futures_feed_ok=False,
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.delete(first)
        session.delete(registry)
        session.delete(commodity)
        session.commit()
    engine.dispose()
