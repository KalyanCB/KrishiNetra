"""Business-key deduplication for weather observation inserts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.weather import WeatherObservationModel
from backend.app.services.ingest.weather.mapper import WeatherObservationDraft

WeatherBusinessKey = tuple[str, date, str]


@dataclass(frozen=True, slots=True)
class WeatherDedupeResult:
    """Drafts split into insert candidates and duplicates."""

    to_insert: list[WeatherObservationDraft]
    skipped: int


def weather_business_key(draft: WeatherObservationDraft) -> WeatherBusinessKey:
    return (draft.region_id, draft.as_of_date, draft.source)


def filter_new_weather_drafts(
    session: Session,
    drafts: list[WeatherObservationDraft],
) -> WeatherDedupeResult:
    """Return drafts whose (region_id, as_of_date, source) is not already stored."""
    if not drafts:
        return WeatherDedupeResult([], 0)

    existing = _load_existing_weather_keys(session, drafts)
    to_insert: list[WeatherObservationDraft] = []
    skipped = 0
    for draft in drafts:
        key = weather_business_key(draft)
        if key in existing:
            skipped += 1
            continue
        to_insert.append(draft)
        existing.add(key)
    return WeatherDedupeResult(to_insert, skipped)


def _load_existing_weather_keys(
    session: Session,
    drafts: list[WeatherObservationDraft],
) -> set[WeatherBusinessKey]:
    region_ids = {draft.region_id for draft in drafts}
    sources = {draft.source for draft in drafts}
    dates = [draft.as_of_date for draft in drafts]
    start = min(dates)
    end = max(dates)

    stmt = select(
        WeatherObservationModel.region_id,
        WeatherObservationModel.as_of_date,
        WeatherObservationModel.source,
    ).where(
        WeatherObservationModel.region_id.in_(region_ids),
        WeatherObservationModel.source.in_(sources),
        WeatherObservationModel.as_of_date >= start,
        WeatherObservationModel.as_of_date <= end,
    )
    rows = session.execute(stmt).all()
    return {(row[0], row[1], row[2]) for row in rows}
