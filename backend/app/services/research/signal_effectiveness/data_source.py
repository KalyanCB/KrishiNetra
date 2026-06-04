"""Load observation panels from @5433 or fixtures (PI10 Track E)."""

from __future__ import annotations

import os
from datetime import date, timedelta

from sqlalchemy.orm import Session

from backend.app.persistence.repositories.observation import (
    ArrivalObservationRepository,
    PriceObservationRepository,
)
from backend.app.persistence.repositories.weather import WeatherObservationRepository
from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_telangana_primary_market_ids,
)
from backend.app.services.ingest.weather.constants import WEATHER_SOURCE_NASA_POWER
from backend.app.services.quality.metrics import VALID_VALIDATION_STATUSES
from backend.app.services.research.signal_effectiveness.panel import ObservationPanel

DEFAULT_WINDOW_START = date(2023, 6, 1)
DEFAULT_WINDOW_END = date(2026, 6, 3)
MIN_VALIDATED_PRICE_ROWS = 100
MIN_EVALUABLE_DAYS = 30


def resolve_data_source(
    session: Session | None = None,
    *,
    commodity_id: str = COTTON_COMMODITY_ID,
    window_start: date | None = None,
    window_end: date | None = None,
) -> ObservationPanel:
    """Prefer validated @5433 corpus; fall back to synthetic fixture panel."""
    start = window_start or DEFAULT_WINDOW_START
    end = window_end or DEFAULT_WINDOW_END

    if session is not None:
        db_panel = try_load_from_database(
            session,
            commodity_id=commodity_id,
            window_start=start,
            window_end=end,
        )
        if db_panel is not None:
            return db_panel

    from backend.app.services.research.signal_effectiveness.synthetic_panel import (
        build_synthetic_observation_panel,
    )

    return build_synthetic_observation_panel(
        window_start=start,
        window_end=end,
    )


def try_load_from_database(
    session: Session,
    *,
    commodity_id: str,
    window_start: date,
    window_end: date,
) -> ObservationPanel | None:
    """Return panel when validated price corpus is sufficient."""
    price_repo = PriceObservationRepository(session)
    arrival_repo = ArrivalObservationRepository(session)
    weather_repo = WeatherObservationRepository(session)

    prices = [
        row
        for row in price_repo.list_by_commodity_date_range(
            commodity_id, window_start, window_end
        )
        if row.validation_status in VALID_VALIDATION_STATUSES
    ]
    if len(prices) < MIN_VALIDATED_PRICE_ROWS:
        return None

    arrivals = [
        row
        for row in arrival_repo.list_by_commodity_date_range(
            commodity_id, window_start, window_end
        )
        if row.validation_status in VALID_VALIDATION_STATUSES
    ]
    weather = weather_repo.list_by_commodity_date_range(
        commodity_id,
        window_start - timedelta(days=365),
        window_end,
        source=WEATHER_SOURCE_NASA_POWER,
    )

    markets = load_telangana_primary_market_ids()
    panel = ObservationPanel(
        prices=tuple(prices),
        arrivals=tuple(arrivals),
        weather=tuple(weather),
        primary_market_ids=markets,
        data_source=_database_source_label(),
        window_start=window_start,
        window_end=window_end,
    )

    from backend.app.services.research.signal_effectiveness.panel import (
        build_daily_panel,
    )

    if len(build_daily_panel(panel)) < MIN_EVALUABLE_DAYS:
        return None
    return panel


def _database_source_label() -> str:
    url = os.environ.get("DATABASE_URL", "")
    if "5433" in url:
        return "postgresql@5433 (validated price_observation)"
    if url:
        return "postgresql (validated price_observation)"
    return "database"
