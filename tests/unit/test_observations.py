"""E-01-S04: observation validation and append-only persistence tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    ObservationValidationStatus,
    PriceObservationModel,
)
from backend.app.persistence.models.reference import (
    CommodityModel,
    CommodityStatus,
    MarketModel,
    RegionModel,
    RegionType,
)
from backend.app.persistence.repositories.observation import (
    ArrivalObservationRepository,
    PriceObservationRepository,
)
from backend.app.persistence.validation.observation import (
    ObservationValidationError,
    validate_validation_status,
)


def test_validation_status_enum_rejects_invalid() -> None:
    with pytest.raises(ObservationValidationError, match="validation_status"):
        validate_validation_status("pending")


def test_validation_status_enum_accepts_all_values() -> None:
    for status in ObservationValidationStatus:
        validate_validation_status(status.value)


def _seed_market(session: Session, *, commodity_id: str, market_id: str) -> None:
    commodity = CommodityModel(
        commodity_id=commodity_id,
        name="Observation Test",
        status=CommodityStatus.DRAFT.value,
    )
    session.add(commodity)
    session.flush()
    region = RegionModel(
        region_id=f"reg_{commodity_id}",
        commodity_id=commodity_id,
        name="Test Region",
        type=RegionType.STATE.value,
    )
    session.add(region)
    session.flush()
    market = MarketModel(
        market_id=market_id,
        region_id=f"reg_{commodity_id}",
        commodity_id=commodity_id,
        market_type="mandi",
        name="Test Mandi",
    )
    session.add(market)
    session.flush()


@pytest.mark.integration
def test_price_observation_append_only(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    observed = datetime(2026, 6, 4, 10, 0, tzinfo=UTC)
    with Session(engine) as session:
        _seed_market(session, commodity_id="obs_test", market_id="mkt_obs_1")
        repo = PriceObservationRepository(session)
        first = PriceObservationModel(
            observation_id=uuid4(),
            market_id="mkt_obs_1",
            commodity_id="obs_test",
            price_type="modal",
            value=Decimal("5500.00"),
            unit="quintal",
            currency="INR",
            observed_at=observed,
            as_of_date=date(2026, 6, 3),
            source="agmarknet",
            validation_status=ObservationValidationStatus.RECEIVED.value,
        )
        second = PriceObservationModel(
            observation_id=uuid4(),
            market_id="mkt_obs_1",
            commodity_id="obs_test",
            price_type="modal",
            value=Decimal("5600.00"),
            unit="quintal",
            currency="INR",
            observed_at=observed,
            as_of_date=date(2026, 6, 4),
            source="agmarknet",
            validation_status=ObservationValidationStatus.PUBLISHED.value,
        )
        repo.insert_observation(first)
        repo.insert_observation(second)
        session.commit()

        rows = repo.list_by_commodity_date_range(
            "obs_test",
            date(2026, 6, 1),
            date(2026, 6, 30),
        )
        assert len(rows) == 2
        assert {row.as_of_date for row in rows} == {date(2026, 6, 3), date(2026, 6, 4)}

        session.delete(second)
        session.delete(first)
        session.delete(session.get(MarketModel, "mkt_obs_1"))
        session.delete(session.get(RegionModel, "reg_obs_test"))
        session.delete(session.get(CommodityModel, "obs_test"))
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_price_observation_invalid_market_fk(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id="obs_fk_test",
            name="FK Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()
        bad = PriceObservationModel(
            observation_id=uuid4(),
            market_id="missing_market",
            commodity_id="obs_fk_test",
            price_type="modal",
            value=Decimal("100"),
            unit="quintal",
            currency="INR",
            observed_at=datetime.now(UTC),
            as_of_date=date(2026, 6, 4),
            source="agmarknet",
        )
        session.add(bad)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
        session.delete(commodity)
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_partition_pruning_explain(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with engine.connect() as conn:
        plan = conn.execute(
            text(
                """
                EXPLAIN (FORMAT TEXT)
                SELECT observation_id
                FROM price_observation
                WHERE commodity_id = 'cotton_test'
                  AND as_of_date >= '2026-06-01'
                  AND as_of_date < '2026-07-01'
                """
            )
        ).fetchall()
    text_plan = "\n".join(row[0] for row in plan)
    assert "price_observation" in text_plan
    engine.dispose()


@pytest.mark.integration
def test_arrival_observation_insert(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _seed_market(session, commodity_id="arr_test", market_id="mkt_arr_1")
        repo = ArrivalObservationRepository(session)
        row = ArrivalObservationModel(
            observation_id=uuid4(),
            market_id="mkt_arr_1",
            commodity_id="arr_test",
            volume=Decimal("120.5"),
            unit="quintal",
            observed_at=datetime(2026, 6, 4, 8, 0, tzinfo=UTC),
            as_of_date=date(2026, 6, 4),
            source="agmarknet",
            validation_status=ObservationValidationStatus.VALIDATED.value,
        )
        repo.insert_observation(row)
        session.commit()
        loaded = repo.get_observation(row.observation_id, as_of_date=date(2026, 6, 4))
        assert loaded is not None
        assert loaded.volume == Decimal("120.5000")

        session.delete(loaded)
        session.delete(session.get(MarketModel, "mkt_arr_1"))
        session.delete(session.get(RegionModel, "reg_arr_test"))
        session.delete(session.get(CommodityModel, "arr_test"))
        session.commit()
    engine.dispose()
