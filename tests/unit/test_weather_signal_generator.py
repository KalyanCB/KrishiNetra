"""E-04-S02: WeatherSignalGenerator deterministic unit tests."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import ObservationValidationStatus
from backend.app.persistence.models.reference import (
    CommodityModel,
    CommodityStatus,
    RegionModel,
    RegionType,
)
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.models.weather import (
    WeatherObservationModel,
    WeatherObservationSource,
)
from backend.app.persistence.repositories.signal import StructuredSignalRepository
from backend.app.persistence.repositories.weather import WeatherObservationRepository
from backend.app.services.ingest.weather.constants import (
    DISTRICT_REGION_IDS,
    region_id_for_district,
)
from backend.app.services.signals.weather.constants import (
    HARVEST_RISK_INDICATOR,
    RAINFALL_DEVIATION,
    RAINFALL_SHOCK,
    TEMPERATURE_STRESS,
)
from backend.app.services.signals.weather.features import (
    compute_harvest_risk_indicator,
    compute_rainfall_deviation,
    compute_rainfall_shock,
    compute_temperature_stress,
    compute_weather_features,
)
from backend.app.services.signals.weather.generator import WeatherSignalGenerator
from backend.app.services.signals.weather.observations import (
    RegionalDailyWeather,
    WeatherObservationSeries,
    select_observations,
)
from shared.domain.enums import AgentType, Direction


def _build_series(
    *,
    as_of: date,
    daily_rain: Decimal,
    daily_temp: Decimal = Decimal("28"),
    daily_rh: Decimal = Decimal("55"),
    regions: int = 5,
) -> WeatherObservationSeries:
    by_date: dict[date, RegionalDailyWeather] = {}
    refs: list[str] = []
    start = as_of - timedelta(days=40)
    day = start
    while day <= as_of:
        by_date[day] = RegionalDailyWeather(
            as_of_date=day,
            rainfall_mm=daily_rain,
            temperature_mean_c=daily_temp,
            relative_humidity_pct=daily_rh,
            observation_ids=(f"obs-{day.isoformat()}",),
        )
        refs.append(f"obs-{day.isoformat()}")
        day += timedelta(days=1)
    return WeatherObservationSeries(
        as_of_date=as_of,
        by_date=by_date,
        regions_expected=5,
        regions_reporting=regions,
        source_observation_refs=tuple(refs),
    )


def test_rainfall_deviation_zero_when_stable() -> None:
    series = _build_series(as_of=date(2026, 6, 4), daily_rain=Decimal("2"))
    assert compute_rainfall_deviation(series) == Decimal("0.0000")


def test_rainfall_shock_spikes_on_wet_day() -> None:
    as_of = date(2026, 6, 4)
    series = _build_series(as_of=as_of, daily_rain=Decimal("1"))
    series.by_date[as_of] = RegionalDailyWeather(
        as_of_date=as_of,
        rainfall_mm=Decimal("25"),
        temperature_mean_c=Decimal("28"),
        relative_humidity_pct=Decimal("55"),
        observation_ids=("obs-spike",),
    )
    shock = compute_rainfall_shock(series)
    assert shock > Decimal("0.5")


def test_temperature_stress_increases_with_heat() -> None:
    series = _build_series(
        as_of=date(2026, 6, 4),
        daily_rain=Decimal("2"),
        daily_temp=Decimal("40"),
    )
    assert compute_temperature_stress(series) == Decimal("1.0000")


def test_harvest_risk_higher_in_october() -> None:
    oct_series = _build_series(
        as_of=date(2025, 10, 15),
        daily_rain=Decimal("12"),
        daily_rh=Decimal("80"),
    )
    jun_series = _build_series(
        as_of=date(2025, 6, 15),
        daily_rain=Decimal("12"),
        daily_rh=Decimal("80"),
    )
    assert compute_harvest_risk_indicator(oct_series) > compute_harvest_risk_indicator(
        jun_series
    )


def test_compute_weather_features_exposes_four_components() -> None:
    features = compute_weather_features(_build_series(as_of=date(2026, 6, 4), daily_rain=Decimal("3")))
    components = features.as_components()
    assert RAINFALL_DEVIATION in components
    assert RAINFALL_SHOCK in components
    assert TEMPERATURE_STRESS in components
    assert HARVEST_RISK_INDICATOR in components
    assert features.magnitude <= Decimal("1")
    assert features.confidence <= Decimal("1")


def test_generate_is_deterministic_for_same_inputs() -> None:
    as_of = date(2026, 6, 4)
    series = _build_series(as_of=as_of, daily_rain=Decimal("4"))
    first = compute_weather_features(series)
    second = compute_weather_features(series)
    assert first == second


def test_select_observations_prefers_validated() -> None:
    as_of = date(2026, 6, 4)
    observed = datetime(2026, 6, 4, 12, 0, tzinfo=UTC)
    region = region_id_for_district("Khammam")
    received = WeatherObservationModel(
        observation_id=uuid4(),
        region_id=region,
        commodity_id="cotton",
        as_of_date=as_of,
        rainfall_mm=Decimal("1"),
        observed_at=observed,
        source=WeatherObservationSource.NASA_POWER.value,
        provenance={},
        validation_status=ObservationValidationStatus.RECEIVED.value,
    )
    validated = WeatherObservationModel(
        observation_id=uuid4(),
        region_id=region,
        commodity_id="cotton",
        as_of_date=as_of,
        rainfall_mm=Decimal("9"),
        observed_at=observed,
        source=WeatherObservationSource.NASA_POWER.value,
        provenance={},
        validation_status=ObservationValidationStatus.VALIDATED.value,
    )
    picked = select_observations(
        [received, validated],
        region_ids=(region,),
        as_of_date=as_of,
    )
    assert len(picked) == 1
    assert picked[0].rainfall_mm == Decimal("9")


def _seed_region(session: Session, *, region_id: str) -> None:
    commodity = session.get(CommodityModel, "cotton")
    if commodity is None:
        session.add(
            CommodityModel(
                commodity_id="cotton",
                name="Cotton",
                status=CommodityStatus.DRAFT.value,
            )
        )
        session.flush()
    if session.get(RegionModel, region_id) is None:
        session.add(
            RegionModel(
                region_id=region_id,
                commodity_id="cotton",
                name=region_id,
                type=RegionType.ZONE.value,
                external_refs={},
            )
        )
        session.flush()


def _insert_weather_row(
    session: Session,
    *,
    region_id: str,
    as_of: date,
    rain: Decimal,
    status: str,
) -> WeatherObservationModel:
    _seed_region(session, region_id=region_id)
    row = WeatherObservationModel(
        observation_id=uuid4(),
        region_id=region_id,
        commodity_id="cotton",
        district_name="Test",
        as_of_date=as_of,
        rainfall_mm=rain,
        temperature_mean_c=Decimal("30"),
        relative_humidity_pct=Decimal("60"),
        observed_at=datetime(as_of.year, as_of.month, as_of.day, 12, 0, tzinfo=UTC),
        source=WeatherObservationSource.NASA_POWER.value,
        provenance={"test": True},
        validation_status=status,
    )
    WeatherObservationRepository(session).insert_observation(row)
    return row


def _seed_registry(session: Session, *, registry_id: UUID) -> None:
    commodity = session.get(CommodityModel, "cotton")
    if commodity is None:
        session.add(
            CommodityModel(
                commodity_id="cotton",
                name="Cotton",
                status=CommodityStatus.DRAFT.value,
            )
        )
        session.flush()
    version = f"1.0.0-test-{registry_id.hex[:8]}"
    existing = session.scalars(
        select(CommodityRegistryModel).where(
            CommodityRegistryModel.commodity_id == "cotton",
            CommodityRegistryModel.version == version,
        )
    ).first()
    if existing is None:
        session.add(
            CommodityRegistryModel(
                registry_id=registry_id,
                commodity_id="cotton",
                version=version,
                effective_from=date(2026, 1, 1),
                is_active=False,
                required_agents=["Market", "Futures"],
                decision_rules={"formula_version": "v1"},
            )
        )
        session.flush()


@pytest.mark.integration
def test_generate_and_persist_weather_signal(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    registry_id = uuid4()
    as_of = date(2026, 6, 3)
    with Session(engine) as session:
        _seed_registry(session, registry_id=registry_id)
        for region_id in DISTRICT_REGION_IDS.values():
            _seed_region(session, region_id=region_id)
            start = as_of - timedelta(days=35)
            day = start
            while day <= as_of:
                _insert_weather_row(
                    session,
                    region_id=region_id,
                    as_of=day,
                    rain=Decimal("2.5"),
                    status=ObservationValidationStatus.VALIDATED.value,
                )
                day += timedelta(days=1)
        session.commit()

        generator = WeatherSignalGenerator(session)
        signal = generator.generate_and_persist(
            as_of_date=as_of,
            registry_id=registry_id,
        )
        session.commit()

        assert signal.agent_type == AgentType.WEATHER.value
        assert signal.magnitude >= Decimal("0")
        assert signal.confidence > Decimal("0")
        assert signal.signal_components is not None
        assert RAINFALL_DEVIATION in signal.signal_components

        loaded = StructuredSignalRepository(session).get_signal(
            signal.signal_id, as_of_date=as_of
        )
        assert loaded is not None
        assert loaded.direction in {
            Direction.BULLISH.value,
            Direction.BEARISH.value,
            Direction.NEUTRAL.value,
        }


def test_confidence_scales_with_region_coverage() -> None:
    full = compute_weather_features(_build_series(as_of=date(2026, 6, 4), daily_rain=Decimal("2")))
    partial = compute_weather_features(
        _build_series(as_of=date(2026, 6, 4), daily_rain=Decimal("2"), regions=2)
    )
    assert partial.confidence < full.confidence


def test_structured_signal_value_matches_sign_times_magnitude() -> None:
    from backend.app.services.signals.common import signed_value

    features = compute_weather_features(
        _build_series(
            as_of=date(2026, 10, 20),
            daily_rain=Decimal("15"),
            daily_rh=Decimal("85"),
        )
    )
    expected = (
        -features.magnitude
        if features.direction == Direction.BEARISH.value
        else features.magnitude
        if features.direction == Direction.BULLISH.value
        else Decimal("0")
    )
    assert signed_value(direction=features.direction, magnitude=features.magnitude) == expected
