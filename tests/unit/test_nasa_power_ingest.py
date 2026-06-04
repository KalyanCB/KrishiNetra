"""PI6 Track D: NASA POWER weather ingest unit tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.persistence.models.weather import WeatherObservationSource
from backend.app.persistence.seeds.runner import SeedRunner
from backend.app.persistence.validation.weather import (
    WeatherValidationError,
    validate_rainfall_mm,
    validate_temperature_mean_c,
)
from backend.app.services.ingest.weather.constants import (
    DISTRICT_REGION_IDS,
    region_id_for_district,
)
from backend.app.services.ingest.weather.dedupe import filter_new_weather_drafts
from backend.app.services.ingest.weather.mapper import map_nasa_power_point
from backend.app.services.ingest.weather.pipeline import (
    NasaPowerIngestPipeline,
    default_ingest_end_date,
    ingest_window_start,
)
from backend.app.spike.weather.constants import TelanganaCottonDistrict
from backend.app.spike.weather.nasa_power import NasaPowerClient, NasaPowerDailyPoint


def _nasa_power_payload(start: str, end: str) -> dict[str, object]:
    return {
        "header": {"fill_value": -999.0, "start": start, "end": end},
        "properties": {
            "parameter": {
                "PRECTOTCORR": {start: 3.28, end: 0.0},
                "T2M": {start: 31.2, end: 32.1},
                "RH2M": {start: 68.0, end: 55.0},
            }
        },
    }


def _mock_nasa_client(*, start: date, end: date) -> NasaPowerClient:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = _nasa_power_payload(
        start.strftime("%Y%m%d"),
        end.strftime("%Y%m%d"),
    )

    mock_http = MagicMock(spec=httpx.Client)
    mock_http.get.return_value = mock_response
    return NasaPowerClient(client=mock_http)


def test_region_mapping_covers_five_districts() -> None:
    assert len(DISTRICT_REGION_IDS) == 5
    assert region_id_for_district("Khammam") == "reg_tg_khammam"
    assert region_id_for_district("Nalgonda") == "reg_tg_nalgonda"


def test_validate_rainfall_rejects_negative() -> None:
    with pytest.raises(WeatherValidationError, match="rainfall_mm"):
        validate_rainfall_mm(-1.0)


def test_validate_temperature_rejects_out_of_range() -> None:
    with pytest.raises(WeatherValidationError, match="temperature_mean_c"):
        validate_temperature_mean_c(60.0)


def test_map_nasa_power_point_builds_draft() -> None:
    point = NasaPowerDailyPoint(
        district="Warangal",
        latitude=17.97,
        longitude=79.59,
        observation_date=date(2024, 6, 1),
        precipitation_mm=3.28,
        temperature_c=31.2,
        relative_humidity_pct=68.0,
    )
    draft = map_nasa_power_point(point)
    assert draft.region_id == "reg_tg_warangal"
    assert draft.commodity_id == "cotton"
    assert draft.rainfall_mm == Decimal("3.28")
    assert draft.temperature_mean_c == Decimal("31.2")
    assert draft.source == WeatherObservationSource.NASA_POWER.value


def test_ingest_window_start_first_of_month() -> None:
    end = date(2025, 5, 31)
    assert ingest_window_start(end, months=36) == date(2022, 5, 1)


def test_default_ingest_end_applies_lag() -> None:
    assert default_ingest_end_date(today=date(2026, 6, 4)) == date(2026, 5, 31)


def test_filter_new_weather_drafts_skips_existing(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        SeedRunner(session).apply("cotton")
        session.flush()
        point = NasaPowerDailyPoint(
            district="Khammam",
            latitude=17.25,
            longitude=79.75,
            observation_date=date(2015, 1, 1),
            precipitation_mm=1.0,
            temperature_c=30.0,
            relative_humidity_pct=50.0,
        )
        draft = map_nasa_power_point(point)
        from backend.app.services.ingest.weather.persist import persist_weather_drafts

        persist_weather_drafts(session, [draft])
        session.commit()

        again = filter_new_weather_drafts(session, [draft])
        assert again.skipped == 1
        assert len(again.to_insert) == 0

        from sqlalchemy import delete

        from backend.app.persistence.models.weather import WeatherObservationModel

        session.execute(
            delete(WeatherObservationModel).where(
                WeatherObservationModel.region_id == draft.region_id,
                WeatherObservationModel.as_of_date == draft.as_of_date,
            )
        )
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_nasa_power_ingest_pipeline_persists(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    district = TelanganaCottonDistrict("Khammam", 17.25, 79.75)
    # Dates outside typical 36-mo backfill to avoid collision with CLI runs.
    start = date(2015, 1, 1)
    end = date(2015, 1, 2)
    with Session(engine) as session:
        pipeline = NasaPowerIngestPipeline(
            session,
            nasa_client=_mock_nasa_client(start=start, end=end),
        )
        result = pipeline.ingest_range(start, end, districts=(district,))
        assert result.points_fetched == 2
        assert result.rows_persisted == 2
        assert result.rows_skipped_duplicate == 0

        rerun = pipeline.ingest_range(start, end, districts=(district,))
        assert rerun.rows_persisted == 0
        assert rerun.rows_skipped_duplicate == 2

        from sqlalchemy import delete

        from backend.app.persistence.models.weather import WeatherObservationModel

        session.execute(
            delete(WeatherObservationModel).where(
                WeatherObservationModel.region_id == "reg_tg_khammam",
                WeatherObservationModel.as_of_date >= start,
                WeatherObservationModel.as_of_date <= end,
            )
        )
        session.commit()
    engine.dispose()


@pytest.mark.integration
def test_nasa_power_live_ingest_single_day() -> None:
    """Optional live NASA POWER + DB persist for one district/day."""
    import os

    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL required")

    from sqlalchemy import create_engine

    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    district = TelanganaCottonDistrict("Khammam", 17.25, 79.75)
    day = date(2024, 6, 1)
    with Session(engine) as session:
        pipeline = NasaPowerIngestPipeline(session)
        result = pipeline.ingest_range(day, day, districts=(district,))
        assert result.points_fetched >= 1
        assert result.rows_persisted + result.rows_skipped_duplicate >= 1
    engine.dispose()
