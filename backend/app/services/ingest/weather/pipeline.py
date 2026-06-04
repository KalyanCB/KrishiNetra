"""NASA POWER ingest pipeline — fetch, map, dedupe, persist."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.app.persistence.seeds.runner import SeedRunner
from backend.app.services.ingest.weather.constants import NASA_POWER_END_LAG_DAYS
from backend.app.services.ingest.weather.dedupe import filter_new_weather_drafts
from backend.app.services.ingest.weather.mapper import map_nasa_power_point
from backend.app.services.ingest.weather.persist import persist_weather_drafts
from backend.app.spike.weather.constants import (
    TELANGANA_COTTON_DISTRICTS,
    TelanganaCottonDistrict,
)
from backend.app.spike.weather.nasa_power import NasaPowerClient, NasaPowerDailyPoint


@dataclass(frozen=True, slots=True)
class NasaPowerIngestResult:
    """Counters from one NASA POWER ingest run."""

    districts_fetched: int
    points_fetched: int
    drafts_mapped: int
    rows_inserted: int
    rows_skipped_duplicate: int

    @property
    def rows_persisted(self) -> int:
        return self.rows_inserted


def default_ingest_end_date(*, today: date | None = None) -> date:
    """Latest inclusive date accounting for NASA POWER publication lag."""
    anchor = today or date.today()
    return anchor - timedelta(days=NASA_POWER_END_LAG_DAYS)


def ingest_window_start(end: date, *, months: int) -> date:
    """Inclusive start date for a backfill window (calendar months)."""
    month = end.month - months
    year = end.year
    while month < 1:
        month += 12
        year -= 1
    return date(year, month, 1)


class NasaPowerIngestPipeline:
    """Orchestrate NASA POWER pulls into weather_observation."""

    def __init__(
        self,
        session: Session,
        *,
        nasa_client: NasaPowerClient | None = None,
        seed_cotton: bool = True,
        write_quality_snapshot: bool = True,
    ) -> None:
        self._session = session
        self._nasa_client = nasa_client or NasaPowerClient()
        self._seed_cotton = seed_cotton
        self._write_quality_snapshot = write_quality_snapshot

    def ingest_range(
        self,
        start: date,
        end: date,
        *,
        districts: tuple[TelanganaCottonDistrict, ...] = TELANGANA_COTTON_DISTRICTS,
        commit: bool = True,
    ) -> NasaPowerIngestResult:
        """Fetch belt districts for [start, end] and persist new observations."""
        if self._seed_cotton:
            SeedRunner(self._session).apply("cotton")
            self._session.flush()

        all_points: list[NasaPowerDailyPoint] = []
        for district in districts:
            points = self._nasa_client.fetch_daily(district, start, end)
            all_points.extend(points)

        drafts = [map_nasa_power_point(point) for point in all_points]
        dedupe = filter_new_weather_drafts(self._session, drafts)
        inserted = persist_weather_drafts(self._session, dedupe.to_insert)
        if self._write_quality_snapshot:
            from backend.app.services.quality.snapshot_service import (
                DataQualitySnapshotService,
            )

            DataQualitySnapshotService(self._session).record_after_weather_ingest(
                as_of_date=end,
                window_start=start,
                window_end=end,
            )
        if commit:
            self._session.commit()

        return NasaPowerIngestResult(
            districts_fetched=len(districts),
            points_fetched=len(all_points),
            drafts_mapped=len(drafts),
            rows_inserted=inserted,
            rows_skipped_duplicate=dedupe.skipped,
        )
