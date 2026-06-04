"""Build daily signal × forward-return panel from observations (PI10 Track E)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    PriceObservationModel,
)
from backend.app.persistence.models.weather import WeatherObservationModel
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_telangana_primary_market_ids,
)
from backend.app.services.research.signal_effectiveness.metrics import (
    FORWARD_HORIZONS_DAYS,
    TRACKED_SIGNALS,
    compute_pct_forward_return,
)
from backend.app.services.signals.market.constants import ROLLING_WINDOW_DAYS
from backend.app.services.signals.market.features import (
    compute_arrival_momentum,
    compute_price_momentum,
)
from backend.app.services.signals.market.generator import (
    MarketSignalGenerator,
    _filter_arrival_observations,
    _filter_price_observations,
)
from backend.app.services.signals.weather.constants import TELANGANA_WEATHER_REGION_IDS
from backend.app.services.signals.weather.features import (
    compute_rainfall_shock,
    compute_temperature_stress,
)
from backend.app.services.signals.weather.observations import (
    RegionalDailyWeather,
    WeatherObservationSeries,
)

MODAL_PRICE_TYPE = "modal"


@dataclass(frozen=True, slots=True)
class ObservationPanel:
    """Validated observation inputs for effectiveness analysis."""

    prices: tuple[PriceObservationModel, ...]
    arrivals: tuple[ArrivalObservationModel, ...]
    weather: tuple[WeatherObservationModel, ...]
    primary_market_ids: tuple[str, ...]
    data_source: str
    window_start: date
    window_end: date


@dataclass(frozen=True, slots=True)
class DailyPanelRow:
    """One evaluable date: four signals and forward price targets."""

    as_of_date: date
    price_momentum: float | None
    arrival_momentum: float | None
    rainfall_shock: float | None
    temperature_stress: float | None
    basket_modal: float | None
    forward_return_7d: float | None
    forward_return_30d: float | None

    def signal_value(self, signal: str) -> float | None:
        value: float | None = getattr(self, signal)
        return value

    def forward_return(self, horizon_days: int) -> float | None:
        if horizon_days == 7:
            return self.forward_return_7d
        if horizon_days == 30:
            return self.forward_return_30d
        msg = f"unsupported horizon {horizon_days}"
        raise ValueError(msg)


def _weather_series_for_date(
    weather_rows: tuple[WeatherObservationModel, ...],
    *,
    as_of_date: date,
    region_ids: tuple[str, ...],
) -> WeatherObservationSeries | None:
    usable = [
        row
        for row in weather_rows
        if row.region_id in region_ids and row.rainfall_mm is not None
    ]
    if not usable:
        return None

    by_region_date: dict[tuple[str, date], WeatherObservationModel] = {}
    for row in usable:
        key = (row.region_id, row.as_of_date)
        current = by_region_date.get(key)
        if current is None or row.as_of_date <= as_of_date:
            by_region_date[key] = row

    daily_buckets: dict[date, list[WeatherObservationModel]] = defaultdict(list)
    for (region_id, day), row in by_region_date.items():
        del region_id
        if day <= as_of_date:
            daily_buckets[day].append(row)

    by_date: dict[date, RegionalDailyWeather] = {}
    refs: list[str] = []
    for day, day_rows in sorted(daily_buckets.items()):
        rains = [row.rainfall_mm for row in day_rows if row.rainfall_mm is not None]
        if not rains:
            continue
        rain_mean = sum(rains, start=Decimal("0")) / Decimal(len(rains))
        temps = [
            row.temperature_mean_c
            for row in day_rows
            if row.temperature_mean_c is not None
        ]
        humidity = [
            row.relative_humidity_pct
            for row in day_rows
            if row.relative_humidity_pct is not None
        ]
        temp_mean = (
            sum(temps, start=Decimal("0")) / Decimal(len(temps)) if temps else None
        )
        rh_mean = (
            sum(humidity, start=Decimal("0")) / Decimal(len(humidity))
            if humidity
            else None
        )
        day_refs = tuple(str(row.observation_id) for row in day_rows)
        refs.extend(day_refs)
        by_date[day] = RegionalDailyWeather(
            as_of_date=day,
            rainfall_mm=rain_mean,
            temperature_mean_c=temp_mean,
            relative_humidity_pct=rh_mean,
            observation_ids=day_refs,
        )

    regions_reporting = sum(
        1
        for region_id in region_ids
        if any(
            row.region_id == region_id and row.as_of_date == as_of_date
            for row in usable
        )
    )
    if as_of_date not in by_date:
        return None

    return WeatherObservationSeries(
        as_of_date=as_of_date,
        by_date=by_date,
        regions_expected=len(region_ids),
        regions_reporting=regions_reporting,
        source_observation_refs=tuple(sorted(set(refs))),
    )


def build_daily_panel(panel: ObservationPanel) -> tuple[DailyPanelRow, ...]:
    """Compute signal values and forward basket-modal returns for each date."""
    markets = panel.primary_market_ids or load_telangana_primary_market_ids()
    prices = _filter_price_observations(list(panel.prices), markets)
    arrivals = _filter_arrival_observations(list(panel.arrivals), markets)

    basket_modals_raw = MarketSignalGenerator._basket_modals_by_date(prices, markets)
    basket_arrivals_raw = MarketSignalGenerator._basket_arrivals_by_date(
        arrivals, markets
    )
    basket_modals = {d: float(v) for d, v in basket_modals_raw.items()}
    basket_arrivals = {d: v for d, v in basket_arrivals_raw.items()}

    if not basket_modals:
        return ()

    ordered_dates = sorted(basket_modals)
    max_horizon = max(FORWARD_HORIZONS_DAYS)
    lookback = ROLLING_WINDOW_DAYS - 1

    rows: list[DailyPanelRow] = []
    for as_of in ordered_dates:
        if as_of < panel.window_start or as_of > panel.window_end:
            continue
        earliest = as_of - timedelta(days=lookback)
        if earliest < ordered_dates[0]:
            continue
        latest_needed = as_of + timedelta(days=max_horizon)
        if latest_needed > ordered_dates[-1]:
            continue

        window_modals = {
            d: Decimal(str(v))
            for d, v in basket_modals.items()
            if earliest <= d <= as_of
        }
        window_arrivals = {
            d: basket_arrivals[d]
            for d in basket_arrivals
            if earliest <= d <= as_of
        }

        price_momentum = compute_price_momentum(
            basket_modals=window_modals,
            as_of_date=as_of,
        )
        arrival_momentum = compute_arrival_momentum(
            basket_arrivals=window_arrivals,
            as_of_date=as_of,
        )

        weather_series = _weather_series_for_date(
            panel.weather,
            as_of_date=as_of,
            region_ids=TELANGANA_WEATHER_REGION_IDS,
        )
        rainfall_shock = None
        temperature_stress = None
        if weather_series is not None:
            rainfall_shock = float(compute_rainfall_shock(weather_series))
            temperature_stress = float(compute_temperature_stress(weather_series))

        spot = basket_modals.get(as_of)
        forward_7 = None
        forward_30 = None
        if spot is not None:
            future_7 = _price_on_or_after(
                basket_modals, as_of + timedelta(days=7), ordered_dates
            )
            future_30 = _price_on_or_after(
                basket_modals, as_of + timedelta(days=30), ordered_dates
            )
            if future_7 is not None:
                forward_7 = compute_pct_forward_return(
                    price_today=spot,
                    price_future=future_7,
                )
            if future_30 is not None:
                forward_30 = compute_pct_forward_return(
                    price_today=spot,
                    price_future=future_30,
                )

        rows.append(
            DailyPanelRow(
                as_of_date=as_of,
                price_momentum=float(price_momentum.raw_value),
                arrival_momentum=float(arrival_momentum.raw_value),
                rainfall_shock=rainfall_shock,
                temperature_stress=temperature_stress,
                basket_modal=spot,
                forward_return_7d=forward_7,
                forward_return_30d=forward_30,
            )
        )

    return tuple(rows)


def _price_on_or_after(
    prices: dict[date, float],
    target: date,
    ordered_dates: list[date],
) -> float | None:
    for day in ordered_dates:
        if day >= target:
            return prices.get(day)
    return None


def panel_summary(rows: tuple[DailyPanelRow, ...]) -> dict[str, int | str | None]:
    """Counts of non-null signal and forward-return cells."""
    counts = {signal: 0 for signal in TRACKED_SIGNALS}
    forward_counts = {f"forward_{h}d": 0 for h in FORWARD_HORIZONS_DAYS}
    for row in rows:
        for signal in TRACKED_SIGNALS:
            if row.signal_value(signal) is not None:
                counts[signal] += 1
        if row.forward_return_7d is not None:
            forward_counts["forward_7d"] += 1
        if row.forward_return_30d is not None:
            forward_counts["forward_30d"] += 1
    return {
        "evaluable_days": len(rows),
        **counts,
        **forward_counts,
        "date_min": rows[0].as_of_date.isoformat() if rows else None,
        "date_max": rows[-1].as_of_date.isoformat() if rows else None,
    }

