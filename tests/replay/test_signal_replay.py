"""PI9 Track D — signal replay validation (Tracks A/B/C)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from tests.fixtures.market_signals import (
    AS_OF_DATE,
    PRIMARY_MARKETS,
    flat_arrival_window,
    registry_fixture,
    rising_price_window,
)
from tests.unit.test_weather_signal_generator import _build_series

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
from backend.app.persistence.repositories.weather import WeatherObservationRepository
from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID
from backend.app.services.ingest.weather.constants import DISTRICT_REGION_IDS
from backend.app.services.signals.market.generator import MarketSignalGenerator
from backend.app.services.signals.replay.harness import (
    DEFAULT_REPLAY_CYCLES,
    ReplayValidationResult,
    fingerprint_combined_snapshot_from_signals,
    fingerprint_to_json,
    fingerprint_weather_cycle,
    run_market_replay,
    run_weather_replay,
    summarize_results,
    validate_replay_cycles,
)
from backend.app.services.signals.weather.generator import WeatherSignalGenerator

REPLAY_CYCLES = DEFAULT_REPLAY_CYCLES
MARKET_AS_OF = AS_OF_DATE
WEATHER_AS_OF = date(2026, 6, 3)


@patch("backend.app.services.signals.market.generator.RegistryService")
def test_market_signal_replay_cycles(mock_registry_cls: MagicMock) -> None:
    """Track A: MarketSignalGenerator — Same Inputs = Same Outputs."""
    registry = registry_fixture(msp_inr_quintal=7121)
    mock_registry_cls.return_value.get_active_config.return_value = registry
    trace_id = uuid4()
    generator = MarketSignalGenerator(MagicMock())

    result = run_market_replay(
        generator,
        cycles=REPLAY_CYCLES,
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=MARKET_AS_OF,
        trace_id=trace_id,
        registry_id=registry.registry_id,
        primary_market_ids=PRIMARY_MARKETS,
        price_observations=rising_price_window(),
        arrival_observations=flat_arrival_window(),
    )

    assert result.passed is True
    assert result.cycles_run == REPLAY_CYCLES
    assert result.mismatches == ()


@patch("backend.app.services.signals.weather.generator.load_observation_series")
def test_weather_signal_replay_cycles(mock_load: MagicMock) -> None:
    """Track B: WeatherSignalGenerator — Same Inputs = Same Outputs."""
    registry_id = uuid4()
    mock_load.return_value = _build_series(
        as_of=WEATHER_AS_OF, daily_rain=Decimal("2.5")
    )
    generator = WeatherSignalGenerator(MagicMock())

    result = run_weather_replay(
        generator,
        cycles=REPLAY_CYCLES,
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=WEATHER_AS_OF,
        registry_id=registry_id,
        trace_id=uuid4(),
    )

    assert result.passed is True
    assert result.cycles_run == REPLAY_CYCLES


@patch("backend.app.services.signals.weather.generator.load_observation_series")
@patch("backend.app.services.signals.market.generator.RegistryService")
def test_combined_snapshot_replay_cycles(
    mock_registry_cls: MagicMock,
    mock_load: MagicMock,
) -> None:
    """Track C: SignalSnapshot PI9 contract — snapshot_hash stable across cycles."""
    registry = registry_fixture(msp_inr_quintal=7121)
    mock_registry_cls.return_value.get_active_config.return_value = registry
    mock_load.return_value = _build_series(
        as_of=WEATHER_AS_OF, daily_rain=Decimal("2.5")
    )

    trace_id = uuid4()
    market_gen = MarketSignalGenerator(MagicMock())
    weather_gen = WeatherSignalGenerator(MagicMock())
    prices = rising_price_window()
    arrivals = flat_arrival_window()

    def _cycle() -> object:
        market_bundle = market_gen.generate(
            as_of_date=MARKET_AS_OF,
            primary_market_ids=PRIMARY_MARKETS,
            price_observations=prices,
            arrival_observations=arrivals,
        )
        weather = weather_gen.generate(
            as_of_date=WEATHER_AS_OF,
            registry_id=registry.registry_id,
            trace_id=trace_id,
        )
        return fingerprint_combined_snapshot_from_signals(
            commodity_id=COTTON_COMMODITY_ID,
            as_of_date=MARKET_AS_OF,
            registry_id=registry.registry_id,
            trace_id=trace_id,
            market_bundle=market_bundle,
            weather=weather,
        )

    result = validate_replay_cycles(
        track="combined_snapshot",
        cycles=REPLAY_CYCLES,
        runner=_cycle,
    )
    assert result.passed is True
    assert result.cycles_run == REPLAY_CYCLES


def test_replay_summary_all_tracks_pass() -> None:
    """Harness summary helper aggregates multi-track results."""
    results = (
        ReplayValidationResult(
            track="market",
            cycles_requested=5,
            cycles_run=5,
            passed=True,
            baseline_fingerprint="abc",
            mismatches=(),
        ),
        ReplayValidationResult(
            track="weather",
            cycles_requested=5,
            cycles_run=5,
            passed=True,
            baseline_fingerprint="def",
            mismatches=(),
        ),
    )
    summary = summarize_results(results)
    assert summary["all_passed"] is True
    assert len(summary["tracks"]) == 2


def _seed_region(session: Session, *, region_id: str, commodity_id: str) -> None:
    if session.get(RegionModel, region_id) is None:
        session.add(
            RegionModel(
                region_id=region_id,
                commodity_id=commodity_id,
                name=region_id,
                type=RegionType.ZONE.value,
                external_refs={},
            )
        )
        session.flush()


def _insert_weather_row(
    session: Session,
    *,
    commodity_id: str,
    region_id: str,
    as_of: date,
    rain: Decimal,
) -> None:
    row = WeatherObservationModel(
        observation_id=uuid4(),
        region_id=region_id,
        commodity_id=commodity_id,
        district_name="Test",
        as_of_date=as_of,
        rainfall_mm=rain,
        temperature_mean_c=Decimal("30"),
        relative_humidity_pct=Decimal("60"),
        observed_at=datetime(as_of.year, as_of.month, as_of.day, 12, 0, tzinfo=UTC),
        source=WeatherObservationSource.NASA_POWER.value,
        provenance={"test": True},
        validation_status=ObservationValidationStatus.VALIDATED.value,
    )
    WeatherObservationRepository(session).insert_observation(row)


def _cleanup_replay_rows(
    session: Session,
    *,
    commodity_id: str,
    as_of_date: date,
) -> None:
    session.execute(
        text(
            "DELETE FROM signal_snapshot WHERE commodity_id = :cid AND as_of_date = :dt"
        ),
        {"cid": commodity_id, "dt": as_of_date},
    )
    session.execute(
        text(
            "DELETE FROM structured_signal WHERE commodity_id = :cid AND as_of_date = :dt"
        ),
        {"cid": commodity_id, "dt": as_of_date},
    )
    session.execute(
        text("DELETE FROM weather_observation WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM commodity_registry WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    commodity = session.get(CommodityModel, commodity_id)
    if commodity is not None:
        session.delete(commodity)
    session.commit()


@pytest.mark.integration
def test_weather_signal_replay_integration_db(migrated_database: str) -> None:
    """Integration: WeatherSignalGenerator replay against DATABASE_URL."""
    commodity_id = f"replay_{uuid4().hex[:8]}"
    registry_id = uuid4()
    trace_id = uuid4()
    as_of = WEATHER_AS_OF

    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        session.add(
            CommodityModel(
                commodity_id=commodity_id,
                name="Replay Test Cotton",
                status=CommodityStatus.DRAFT.value,
            )
        )
        session.add(
            CommodityRegistryModel(
                registry_id=registry_id,
                commodity_id=commodity_id,
                version="1.0.0-replay",
                effective_from=date(2026, 1, 1),
                is_active=True,
                required_agents=["Market", "Weather"],
                decision_rules={"formula_version": "v1", "msp_inr_quintal": 7121},
            )
        )
        session.flush()

        for region_id in DISTRICT_REGION_IDS.values():
            _seed_region(session, region_id=region_id, commodity_id=commodity_id)
            start = as_of - timedelta(days=365)
            day = start
            while day <= as_of:
                _insert_weather_row(
                    session,
                    commodity_id=commodity_id,
                    region_id=region_id,
                    as_of=day,
                    rain=Decimal("2.5"),
                )
                day += timedelta(days=1)
        session.commit()

        weather_gen = WeatherSignalGenerator(session)
        fingerprints: list[str] = []
        for _ in range(REPLAY_CYCLES):
            signal = weather_gen.generate(
                commodity_id=commodity_id,
                as_of_date=as_of,
                registry_id=registry_id,
                trace_id=trace_id,
            )
            fingerprints.append(fingerprint_to_json(fingerprint_weather_cycle(signal)))

        assert len(set(fingerprints)) == 1

        _cleanup_replay_rows(session, commodity_id=commodity_id, as_of_date=as_of)
    engine.dispose()
