"""Append-only persistence for mapped NASA POWER weather drafts."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.persistence.repositories.weather import WeatherObservationRepository
from backend.app.services.ingest.weather.mapper import (
    WeatherObservationDraft,
    weather_model_from_draft,
)


def persist_weather_drafts(
    session: Session,
    drafts: list[WeatherObservationDraft],
) -> int:
    """Insert weather drafts via append-only repository."""
    if not drafts:
        return 0
    repo = WeatherObservationRepository(session)
    for draft in drafts:
        repo.insert_observation(weather_model_from_draft(draft))
    return len(drafts)
