"""PI8 Track A: observation validation pipeline tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
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
from backend.app.persistence.validation.agmarknet_observation import (
    validate_arrival_observation_fields,
    validate_price_observation_fields,
)
from backend.app.persistence.validation.observation import validate_validation_status
from backend.app.services.validation.observation_validation_service import (
    ObservationValidationService,
)


def test_validation_status_accepts_rejected() -> None:
    validate_validation_status(ObservationValidationStatus.REJECTED.value)


def test_validate_price_observation_passes_clean_row() -> None:
    outcome = validate_price_observation_fields(
        market_id="mkt_tg_khammam_apmc",
        commodity_id="cotton",
        price_type="modal",
        value=Decimal("5500"),
        unit="quintal",
        currency="INR",
        observed_at=datetime(2026, 6, 3, 18, 30, tzinfo=UTC),
        as_of_date=date(2026, 6, 3),
        source="agmarknet",
        known_market_ids=frozenset({"mkt_tg_khammam_apmc"}),
        known_commodity_ids=frozenset({"cotton"}),
    )
    assert outcome.passed
    assert outcome.issues == ()


def test_validate_price_observation_rejects_out_of_range() -> None:
    outcome = validate_price_observation_fields(
        market_id="mkt_tg_khammam_apmc",
        commodity_id="cotton",
        price_type="modal",
        value=Decimal("1"),
        unit="quintal",
        currency="INR",
        observed_at=datetime(2026, 6, 3, 18, 30, tzinfo=UTC),
        as_of_date=date(2026, 6, 3),
        source="agmarknet",
        known_market_ids=frozenset({"mkt_tg_khammam_apmc"}),
        known_commodity_ids=frozenset({"cotton"}),
    )
    assert not outcome.passed
    assert any(issue.check == "price_range" for issue in outcome.issues)


def test_validate_price_observation_rejects_unknown_market() -> None:
    outcome = validate_price_observation_fields(
        market_id="missing_market",
        commodity_id="cotton",
        price_type="modal",
        value=Decimal("5500"),
        unit="quintal",
        currency="INR",
        observed_at=datetime(2026, 6, 3, 18, 30, tzinfo=UTC),
        as_of_date=date(2026, 6, 3),
        source="agmarknet",
        known_market_ids=frozenset({"mkt_tg_khammam_apmc"}),
        known_commodity_ids=frozenset({"cotton"}),
    )
    assert not outcome.passed
    assert any(issue.check == "market_mapping" for issue in outcome.issues)


def test_validate_arrival_observation_rejects_date_lag() -> None:
    outcome = validate_arrival_observation_fields(
        market_id="mkt_tg_khammam_apmc",
        commodity_id="cotton",
        volume=Decimal("120"),
        unit="quintal",
        observed_at=datetime(2026, 6, 10, 18, 30, tzinfo=UTC),
        as_of_date=date(2026, 6, 3),
        source="agmarknet",
        known_market_ids=frozenset({"mkt_tg_khammam_apmc"}),
        known_commodity_ids=frozenset({"cotton"}),
    )
    assert not outcome.passed
    assert any(issue.check == "date_consistency" for issue in outcome.issues)


def _seed_market(session: Session, *, commodity_id: str, market_id: str) -> None:
    if session.get(CommodityModel, commodity_id) is None:
        commodity = CommodityModel(
            commodity_id=commodity_id,
            name="Validation Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()
    region_id = f"reg_{commodity_id}"
    if session.get(RegionModel, region_id) is None:
        region = RegionModel(
            region_id=region_id,
            commodity_id=commodity_id,
            name="Test Region",
            type=RegionType.STATE.value,
        )
        session.add(region)
        session.flush()
    if session.get(MarketModel, market_id) is None:
        market = MarketModel(
            market_id=market_id,
            region_id=region_id,
            commodity_id=commodity_id,
            market_type="mandi",
            name="Test Mandi",
        )
        session.add(market)
        session.flush()


@pytest.mark.integration
def test_batch_validation_updates_status(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    market_id = "mkt_val_batch"
    commodity_id = "cotton"
    as_of = date(2026, 6, 4)
    observed = datetime(2026, 6, 4, 18, 30, tzinfo=UTC)
    with Session(engine) as session:
        _seed_market(session, commodity_id=commodity_id, market_id=market_id)
        price_repo = PriceObservationRepository(session)
        arrival_repo = ArrivalObservationRepository(session)
        price_repo.insert_observation(
            PriceObservationModel(
                observation_id=uuid4(),
                market_id=market_id,
                commodity_id=commodity_id,
                price_type="modal",
                value=Decimal("5500"),
                unit="quintal",
                currency="INR",
                observed_at=observed,
                as_of_date=as_of,
                source="agmarknet",
                validation_status=ObservationValidationStatus.RECEIVED.value,
            )
        )
        price_repo.insert_observation(
            PriceObservationModel(
                observation_id=uuid4(),
                market_id=market_id,
                commodity_id=commodity_id,
                price_type="modal",
                value=Decimal("1"),
                unit="quintal",
                currency="INR",
                observed_at=observed,
                as_of_date=as_of,
                source="agmarknet",
                validation_status=ObservationValidationStatus.RECEIVED.value,
            )
        )
        arrival_repo.insert_observation(
            ArrivalObservationModel(
                observation_id=uuid4(),
                market_id=market_id,
                commodity_id=commodity_id,
                volume=Decimal("50"),
                unit="quintal",
                observed_at=observed,
                as_of_date=as_of,
                source="agmarknet",
                validation_status=ObservationValidationStatus.RECEIVED.value,
            )
        )
        session.commit()

        service = ObservationValidationService(session)
        result = service.validate_pending(
            commodity_id=commodity_id,
            source="agmarknet",
            window_start=as_of,
            window_end=as_of,
            dry_run=False,
        )
        session.commit()

        assert result.price.examined == 2
        assert result.price.validated == 1
        assert result.price.rejected == 1
        assert result.arrival.validated == 1
        assert result.arrival.rejected == 0

        statuses = session.scalars(
            select(PriceObservationModel.validation_status).where(
                PriceObservationModel.commodity_id == commodity_id,
                PriceObservationModel.market_id == market_id,
                PriceObservationModel.as_of_date == as_of,
            )
        ).all()
        assert ObservationValidationStatus.VALIDATED.value in statuses
        assert ObservationValidationStatus.REJECTED.value in statuses

        for row in session.scalars(
            select(ArrivalObservationModel).where(
                ArrivalObservationModel.market_id == market_id,
            )
        ).all():
            session.delete(row)
        for row in session.scalars(
            select(PriceObservationModel).where(
                PriceObservationModel.market_id == market_id,
            )
        ).all():
            session.delete(row)
        session.flush()
        market = session.get(MarketModel, market_id)
        if market is not None:
            session.delete(market)
        session.commit()
    engine.dispose()
