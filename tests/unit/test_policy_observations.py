"""PI10 Track B: policy observation validation and append-only persistence tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import ObservationValidationStatus
from backend.app.persistence.models.policy import (
    PolicyObservationModel,
    PolicyObservationSource,
    PolicyType,
)
from backend.app.persistence.models.reference import (
    CommodityModel,
    CommodityStatus,
)
from backend.app.persistence.repositories.policy import PolicyObservationRepository
from backend.app.persistence.seeds.policy import PolicySeedRunner
from backend.app.persistence.validation.policy import (
    PolicyValidationError,
    validate_policy_confidence,
    validate_policy_impact_direction,
    validate_policy_source,
    validate_policy_type,
)


def test_policy_type_rejects_unknown() -> None:
    with pytest.raises(PolicyValidationError, match="policy_type"):
        validate_policy_type("subsidy_hike")


def test_policy_type_accepts_catalog() -> None:
    for policy_type in PolicyType:
        validate_policy_type(policy_type.value)


def test_policy_source_accepts_catalog() -> None:
    for source in PolicyObservationSource:
        validate_policy_source(source.value)


def test_policy_impact_direction_accepts_signal_directions() -> None:
    for direction in ("bullish", "bearish", "neutral"):
        validate_policy_impact_direction(direction)


def test_policy_confidence_rejects_out_of_range() -> None:
    with pytest.raises(PolicyValidationError, match="confidence"):
        validate_policy_confidence(Decimal("1.5"))


def _seed_cotton(session: Session, *, commodity_id: str = "pol_test_cotton") -> None:
    if session.get(CommodityModel, commodity_id) is None:
        session.add(
            CommodityModel(
                commodity_id=commodity_id,
                name="Policy Test Cotton",
                status=CommodityStatus.DRAFT.value,
            )
        )
        session.flush()


@pytest.mark.integration
def test_policy_observation_append_only(migrated_database: str) -> None:
    commodity_id = f"pol_test_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _seed_cotton(session, commodity_id=commodity_id)
        repo = PolicyObservationRepository(session)
        row = PolicyObservationModel(
            observation_id=uuid4(),
            commodity_id=commodity_id,
            policy_type=PolicyType.MSP_ANNOUNCEMENT.value,
            source=PolicyObservationSource.PIB_MANUAL.value,
            published_date=date(2026, 5, 15),
            effective_date=date(2026, 6, 1),
            impact_direction="bullish",
            confidence=Decimal("0.8500"),
            summary="MSP stub",
            validation_status=ObservationValidationStatus.VALIDATED.value,
        )
        repo.insert_observation(row)
        session.commit()

        loaded = repo.get_observation(row.observation_id)
        assert loaded is not None
        assert loaded.policy_type == PolicyType.MSP_ANNOUNCEMENT.value
        assert loaded.impact_direction == "bullish"

        listed = repo.list_by_commodity_date_range(
            commodity_id,
            date(2026, 6, 1),
            date(2026, 6, 30),
            policy_type=PolicyType.MSP_ANNOUNCEMENT.value,
        )
        assert len(listed) == 1
        assert listed[0].observation_id == row.observation_id


@pytest.mark.integration
def test_policy_seed_fixture_idempotent(migrated_database: str) -> None:
    from sqlalchemy import text

    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        from backend.app.persistence.seeds.runner import SeedRunner

        session.execute(
            text("DELETE FROM policy_observation WHERE commodity_id = 'cotton'")
        )
        SeedRunner(session).apply("cotton")
        session.flush()
        runner = PolicySeedRunner(session)
        first = runner.apply("policy_cotton")
        session.commit()
        assert first == 2

    with Session(engine) as session:
        second = PolicySeedRunner(session).apply("policy_cotton")
        session.commit()
        assert second == 0

    with Session(engine) as session:
        rows = PolicyObservationRepository(session).list_by_commodity_date_range(
            "cotton",
            date(2026, 1, 1),
            date(2026, 12, 31),
        )
        types = {row.policy_type for row in rows}
        assert PolicyType.MSP_ANNOUNCEMENT.value in types
        assert PolicyType.EXPORT_BAN.value in types
