"""PI6 Track C: weather observation validation and append-only persistence tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import ObservationValidationStatus
from backend.app.persistence.models.reference import (
    CommodityModel,
    CommodityStatus,
    RegionModel,
    RegionType,
)
from backend.app.persistence.models.weather import (
    WeatherObservationModel,
    WeatherObservationSource,
)
from backend.app.persistence.repositories.weather import WeatherObservationRepository
from backend.app.persistence.validation.weather import (
    WeatherValidationError,
    validate_rainfall_mm,
    validate_temperature_mean_c,
    validate_weather_source,
)


def test_weather_source_rejects_invalid() -> None:
    with pytest.raises(WeatherValidationError, match="source"):
        validate_weather_source("era5")


def test_weather_source_accepts_nasa_power_and_imd() -> None:
    for source in WeatherObservationSource:
        validate_weather_source(source.value)


def test_validate_rainfall_and_temperature_accept_spike_sample() -> None:
    validate_rainfall_mm(Decimal("3.2800"))
    validate_temperature_mean_c(Decimal("35.38"))


def _seed_region(session: Session, *, commodity_id: str, region_id: str) -> None:
    commodity = CommodityModel(
        commodity_id=commodity_id,
        name="Weather Test",
        status=CommodityStatus.DRAFT.value,
    )
    session.add(commodity)
    session.flush()
    region = RegionModel(
        region_id=region_id,
        commodity_id=commodity_id,
        name="Khammam",
        type=RegionType.ZONE.value,
        external_refs={"imd_obj_id": "164"},
    )
    session.add(region)
    session.flush()


@pytest.mark.integration
def test_weather_observation_append_only(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    observed = datetime(2026, 6, 4, 12, 0, tzinfo=UTC)
    with Session(engine) as session:
        _seed_region(session, commodity_id="wx_test", region_id="reg_wx_khammam")
        repo = WeatherObservationRepository(session)
        nasa_row = WeatherObservationModel(
            observation_id=uuid4(),
            region_id="reg_wx_khammam",
            commodity_id="wx_test",
            district_name="Khammam",
            as_of_date=date(2026, 6, 3),
            rainfall_mm=Decimal("3.2800"),
            temperature_mean_c=Decimal("35.38"),
            relative_humidity_pct=Decimal("43.51"),
            observed_at=observed,
            source=WeatherObservationSource.NASA_POWER.value,
            provenance={
                "api": "nasa_power_daily_point",
                "latitude": 17.25,
                "longitude": 79.75,
                "parameters": ["PRECTOTCORR", "T2M", "RH2M"],
            },
            validation_status=ObservationValidationStatus.RECEIVED.value,
        )
        imd_row = WeatherObservationModel(
            observation_id=uuid4(),
            region_id="reg_wx_khammam",
            commodity_id="wx_test",
            district_name="Khammam",
            as_of_date=date(2026, 6, 4),
            rainfall_mm=Decimal("0.00"),
            temperature_min_c=Decimal("22.00"),
            temperature_max_c=Decimal("34.00"),
            temperature_mean_c=Decimal("28.00"),
            observed_at=observed,
            source=WeatherObservationSource.IMD.value,
            provenance={
                "imd_obj_id": "164",
                "daily_normal_mm": "1.70",
                "daily_departure_pct": "-100%",
            },
            validation_status=ObservationValidationStatus.VALIDATED.value,
        )
        repo.insert_observation(nasa_row)
        repo.insert_observation(imd_row)
        session.commit()

        by_region = repo.list_by_region_date_range(
            "reg_wx_khammam",
            date(2026, 6, 1),
            date(2026, 6, 30),
        )
        assert len(by_region) == 2
        assert {row.source for row in by_region} == {
            WeatherObservationSource.NASA_POWER.value,
            WeatherObservationSource.IMD.value,
        }

        nasa_only = repo.list_by_commodity_date_range(
            "wx_test",
            date(2026, 6, 1),
            date(2026, 6, 30),
            source=WeatherObservationSource.NASA_POWER.value,
        )
        assert len(nasa_only) == 1
        assert nasa_only[0].temperature_mean_c == Decimal("35.38")

        session.delete(imd_row)
        session.delete(nasa_row)
        session.delete(session.get(RegionModel, "reg_wx_khammam"))
        session.delete(session.get(CommodityModel, "wx_test"))
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_weather_observation_invalid_region_fk(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        commodity = CommodityModel(
            commodity_id="wx_fk_test",
            name="FK Test",
            status=CommodityStatus.DRAFT.value,
        )
        session.add(commodity)
        session.flush()
        bad = WeatherObservationModel(
            observation_id=uuid4(),
            region_id="missing_region",
            commodity_id="wx_fk_test",
            as_of_date=date(2026, 6, 4),
            rainfall_mm=Decimal("1.0"),
            observed_at=datetime.now(UTC),
            source=WeatherObservationSource.NASA_POWER.value,
            provenance={},
        )
        session.add(bad)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    engine.dispose()


@pytest.mark.integration
def test_weather_observation_repository_rejects_invalid_source(
    migrated_database: str,
) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        _seed_region(session, commodity_id="wx_val", region_id="reg_wx_val")
        session.commit()
        repo = WeatherObservationRepository(session)
        row = WeatherObservationModel(
            observation_id=uuid4(),
            region_id="reg_wx_val",
            commodity_id="wx_val",
            as_of_date=date(2026, 6, 4),
            observed_at=datetime.now(UTC),
            source="openweather",
            provenance={},
        )
        with pytest.raises(WeatherValidationError, match="source"):
            repo.insert_observation(row)
        region = session.get(RegionModel, "reg_wx_val")
        commodity = session.get(CommodityModel, "wx_val")
        assert region is not None and commodity is not None
        session.delete(region)
        session.delete(commodity)
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_weather_partition_parent_present(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with engine.connect() as conn:
        child = conn.execute(
            text(
                """
                SELECT inhrelid::regclass::text AS child
                FROM pg_inherits
                WHERE inhparent = 'weather_observation'::regclass
                ORDER BY 1
                """
            )
        ).fetchall()
    children = {row[0] for row in child}
    assert "weather_observation_2026_06" in children
    assert "weather_observation_default" in children
    engine.dispose()
