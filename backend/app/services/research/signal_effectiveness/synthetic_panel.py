"""Synthetic observation panel when @5433 corpus is insufficient (PI10 Track E)."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    ObservationValidationStatus,
    PriceObservationModel,
)
from backend.app.persistence.models.weather import (
    WeatherObservationModel,
    WeatherObservationSource,
)
from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    DEFAULT_ARRIVAL_UNIT,
    DEFAULT_CURRENCY,
    DEFAULT_PRICE_UNIT,
    SOURCE_AGMARKNET,
)
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_telangana_primary_market_ids,
)
from backend.app.services.ingest.weather.constants import DISTRICT_REGION_IDS
from backend.app.services.research.signal_effectiveness.panel import ObservationPanel

FIXTURE_DATA_SOURCE = "synthetic_fixture_panel (5433 corpus insufficient)"


def build_synthetic_observation_panel(
    *,
    window_start: date | None = None,
    window_end: date | None = None,
    pad_days: int = 40,
) -> ObservationPanel:
    """Build a deterministic multi-market panel with trend + seasonality."""
    eval_start = window_start or date(2024, 10, 1)
    eval_end = window_end or date(2025, 11, 30)
    data_start = eval_start - timedelta(days=pad_days + 30)
    data_end = eval_end + timedelta(days=40)

    markets = load_telangana_primary_market_ids()
    prices: list[PriceObservationModel] = []
    arrivals: list[ArrivalObservationModel] = []
    weather: list[WeatherObservationModel] = []

    day = data_start
    idx = 0
    while day <= data_end:
        base = 6800.0 + idx * 2.5 + 120.0 * math.sin(idx / 18.0) + 40.0 * math.sin(idx / 5.0)
        for market_offset, market_id in enumerate(markets):
            modal = Decimal(str(round(base + market_offset * 15.0, 2)))
            prices.append(
                PriceObservationModel(
                    observation_id=uuid4(),
                    as_of_date=day,
                    market_id=market_id,
                    commodity_id=COTTON_COMMODITY_ID,
                    price_type="modal",
                    value=modal,
                    unit=DEFAULT_PRICE_UNIT,
                    currency=DEFAULT_CURRENCY,
                    observed_at=datetime(
                        day.year, day.month, day.day, 12, 0, tzinfo=UTC
                    ),
                    source=SOURCE_AGMARKNET,
                    validation_status=ObservationValidationStatus.VALIDATED.value,
                )
            )

        in_season = day.month in {10, 11, 12, 1, 2, 3}
        arrival_base = 80.0 if in_season else 12.0
        arrival_vol = arrival_base + 25.0 * abs(math.sin(idx / 7.0))
        for market_id in markets:
            arrivals.append(
                ArrivalObservationModel(
                    observation_id=uuid4(),
                    as_of_date=day,
                    market_id=market_id,
                    commodity_id=COTTON_COMMODITY_ID,
                    volume=Decimal(str(round(arrival_vol, 2))),
                    unit=DEFAULT_ARRIVAL_UNIT,
                    observed_at=datetime(
                        day.year, day.month, day.day, 12, 0, tzinfo=UTC
                    ),
                    source=SOURCE_AGMARKNET,
                    validation_status=ObservationValidationStatus.VALIDATED.value,
                )
            )

        rain_base = 2.0 + 3.0 * abs(math.sin(idx / 11.0))
        if idx % 23 == 0:
            rain_base += 18.0
        temp_c = 28.0 + 6.0 * math.sin(idx / 13.0)
        rh = 55.0 + 10.0 * math.cos(idx / 9.0)
        for region_id in DISTRICT_REGION_IDS.values():
            weather.append(
                WeatherObservationModel(
                    observation_id=uuid4(),
                    region_id=region_id,
                    commodity_id=COTTON_COMMODITY_ID,
                    district_name=region_id,
                    as_of_date=day,
                    rainfall_mm=Decimal(str(round(rain_base, 2))),
                    temperature_mean_c=Decimal(str(round(temp_c, 2))),
                    relative_humidity_pct=Decimal(str(round(rh, 2))),
                    observed_at=datetime(
                        day.year, day.month, day.day, 12, 0, tzinfo=UTC
                    ),
                    source=WeatherObservationSource.NASA_POWER.value,
                    provenance={"fixture": "signal_effectiveness"},
                    validation_status=ObservationValidationStatus.VALIDATED.value,
                )
            )

        day += timedelta(days=1)
        idx += 1

    return ObservationPanel(
        prices=tuple(prices),
        arrivals=tuple(arrivals),
        weather=tuple(weather),
        primary_market_ids=markets,
        data_source=FIXTURE_DATA_SOURCE,
        window_start=eval_start,
        window_end=eval_end,
    )
