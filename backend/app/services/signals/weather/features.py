"""Deterministic weather feature transforms (E-04-S02)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from backend.app.services.signals.common import clip_signed, clip_unit, quantize
from backend.app.services.signals.weather.constants import (
    HARVEST_RAIN_7D_REFERENCE_MM,
    HARVEST_RISK_INDICATOR,
    PRIMARY_DRIVER,
    PRIMARY_DRIVER_THRESHOLD,
    RAINFALL_DEVIATION,
    RAINFALL_SHOCK,
    RAINFALL_SHOCK_FLOOR_MM,
    STAGE_WEIGHT_HIGH,
    STAGE_WEIGHT_LOW,
    STAGE_WEIGHT_MEDIUM,
    TEMPERATURE_OPTIMAL_C,
    TEMPERATURE_STRESS,
    TEMPERATURE_STRESS_BAND_C,
)
from backend.app.services.signals.weather.observations import WeatherObservationSeries
from shared.domain.enums import Direction

# Harvest / storage calendar windows (COTTON_LIFECYCLE_SIGNAL_MAPPING §4–§5).
HARVEST_MONTHS = frozenset({10, 11, 12, 1, 2})
GROWTH_MONTHS = frozenset({8, 9})
SOWING_MONTHS = frozenset({6, 7})
STORAGE_MONTHS = frozenset({11, 12, 1, 2, 3})


@dataclass(frozen=True, slots=True)
class WeatherFeatureSet:
    """Four deterministic sub-signals plus composite metadata."""

    rainfall_deviation: Decimal
    rainfall_shock: Decimal
    temperature_stress: Decimal
    harvest_risk_indicator: Decimal
    primary_driver: str
    direction: str
    magnitude: Decimal
    confidence: Decimal
    stage_weight: Decimal
    regions_reporting: int
    regions_expected: int

    def as_components(self) -> dict[str, object]:
        return {
            RAINFALL_DEVIATION: float(self.rainfall_deviation),
            RAINFALL_SHOCK: float(self.rainfall_shock),
            TEMPERATURE_STRESS: float(self.temperature_stress),
            HARVEST_RISK_INDICATOR: float(self.harvest_risk_indicator),
            PRIMARY_DRIVER: self.primary_driver,
            "regions_reporting": self.regions_reporting,
            "regions_expected": self.regions_expected,
            "stage_weight": float(self.stage_weight),
        }


def stage_weight_for_month(month: int) -> Decimal:
    """Lifecycle stage weight H/M/L (COTTON_LIFECYCLE_SIGNAL_MAPPING §6)."""
    if month in HARVEST_MONTHS or month in GROWTH_MONTHS:
        return STAGE_WEIGHT_HIGH
    if month in SOWING_MONTHS or month in STORAGE_MONTHS:
        return STAGE_WEIGHT_MEDIUM
    return STAGE_WEIGHT_LOW


def _daily_rainfall(series: WeatherObservationSeries, day: date) -> Decimal | None:
    row = series.by_date.get(day)
    if row is None:
        return None
    return row.rainfall_mm


def _mean_rainfall(series: WeatherObservationSeries, start: date, end: date) -> Decimal | None:
    values: list[Decimal] = []
    day = start
    while day <= end:
        rain = _daily_rainfall(series, day)
        if rain is not None:
            values.append(rain)
        day += timedelta(days=1)
    if not values:
        return None
    return sum(values, start=Decimal("0")) / Decimal(len(values))


def _sum_rainfall(series: WeatherObservationSeries, start: date, end: date) -> Decimal:
    total = Decimal("0")
    day = start
    while day <= end:
        rain = _daily_rainfall(series, day)
        if rain is not None:
            total += rain
        day += timedelta(days=1)
    return total


def compute_rainfall_deviation(series: WeatherObservationSeries) -> Decimal:
    """Departure of 30d mean rainfall vs trailing 30d norm — scaled to [-1, 1]."""
    as_of = series.as_of_date
    window_start = as_of - timedelta(days=29)
    norm_end = as_of - timedelta(days=30)
    norm_start = norm_end - timedelta(days=29)

    actual_mean = _mean_rainfall(series, window_start, as_of)
    norm_mean = _mean_rainfall(series, norm_start, norm_end)
    if actual_mean is None or norm_mean is None:
        return Decimal("0")

    denominator = norm_mean if norm_mean > Decimal("0") else Decimal("1")
    raw = (actual_mean - norm_mean) / denominator
    return clip_signed(raw)


def compute_rainfall_shock(series: WeatherObservationSeries) -> Decimal:
    """Day-over-week mean rainfall spike — [0, 1]."""
    as_of = series.as_of_date
    today = _daily_rainfall(series, as_of)
    if today is None:
        return Decimal("0")

    prior_start = as_of - timedelta(days=7)
    prior_end = as_of - timedelta(days=1)
    prior_mean = _mean_rainfall(series, prior_start, prior_end)
    if prior_mean is None:
        return Decimal("0")

    delta = abs(today - prior_mean)
    denominator = prior_mean if prior_mean > RAINFALL_SHOCK_FLOOR_MM else RAINFALL_SHOCK_FLOOR_MM
    return clip_unit(delta / denominator)


def compute_temperature_stress(series: WeatherObservationSeries) -> Decimal:
    """Deviation from cotton-belt optimal daily mean temperature — [0, 1]."""
    row = series.by_date.get(series.as_of_date)
    if row is None or row.temperature_mean_c is None:
        return Decimal("0")
    delta = abs(row.temperature_mean_c - TEMPERATURE_OPTIMAL_C)
    return clip_unit(delta / TEMPERATURE_STRESS_BAND_C)


def compute_harvest_risk_indicator(series: WeatherObservationSeries) -> Decimal:
    """Rain + humidity composite during harvest/storage windows — [0, 1]."""
    as_of = series.as_of_date
    rain_start = as_of - timedelta(days=6)
    rain_7d = _sum_rainfall(series, rain_start, as_of)
    rain_component = clip_unit(rain_7d / HARVEST_RAIN_7D_REFERENCE_MM)

    row = series.by_date.get(as_of)
    humidity_component = Decimal("0")
    if row is not None and row.relative_humidity_pct is not None:
        excess = row.relative_humidity_pct - Decimal("50")
        if excess > Decimal("0"):
            humidity_component = clip_unit(excess / Decimal("40"))

    base = quantize(Decimal("0.6") * rain_component + Decimal("0.4") * humidity_component)
    month = as_of.month
    if month not in HARVEST_MONTHS and month not in STORAGE_MONTHS:
        return clip_unit(base * STAGE_WEIGHT_LOW)
    return clip_unit(base)


def _weighted_score(name: str, value: Decimal, stage_weight: Decimal) -> tuple[str, Decimal]:
    if name == RAINFALL_DEVIATION:
        return name, abs(value) * stage_weight
    return name, value * stage_weight


def resolve_primary_driver(
    *,
    rainfall_deviation: Decimal,
    rainfall_shock: Decimal,
    temperature_stress: Decimal,
    harvest_risk_indicator: Decimal,
    stage_weight: Decimal,
) -> str:
    candidates = [
        _weighted_score(RAINFALL_DEVIATION, rainfall_deviation, stage_weight),
        _weighted_score(RAINFALL_SHOCK, rainfall_shock, stage_weight),
        _weighted_score(TEMPERATURE_STRESS, temperature_stress, stage_weight),
        _weighted_score(HARVEST_RISK_INDICATOR, harvest_risk_indicator, stage_weight),
    ]
    candidates.sort(key=lambda item: (item[1], item[0]), reverse=True)
    return candidates[0][0]


def direction_for_driver(
    driver: str,
    *,
    rainfall_deviation: Decimal,
    rainfall_shock: Decimal,
    temperature_stress: Decimal,
    harvest_risk_indicator: Decimal,
    month: int,
) -> str:
    """Map primary_driver to TDS-004 direction (SIGNAL_ENGINE_V1 §4.3)."""
    if driver == RAINFALL_DEVIATION:
        if rainfall_deviation < -PRIMARY_DRIVER_THRESHOLD and month in GROWTH_MONTHS:
            return Direction.BULLISH.value
        if rainfall_deviation > PRIMARY_DRIVER_THRESHOLD:
            return Direction.BEARISH.value
        return Direction.NEUTRAL.value

    if driver == RAINFALL_SHOCK:
        if rainfall_shock > PRIMARY_DRIVER_THRESHOLD:
            return Direction.BEARISH.value
        return Direction.NEUTRAL.value

    if driver == TEMPERATURE_STRESS:
        if temperature_stress > PRIMARY_DRIVER_THRESHOLD:
            if month in GROWTH_MONTHS:
                return Direction.BULLISH.value
            return Direction.BEARISH.value
        return Direction.NEUTRAL.value

    if driver == HARVEST_RISK_INDICATOR:
        if harvest_risk_indicator > PRIMARY_DRIVER_THRESHOLD:
            return Direction.BEARISH.value
        if harvest_risk_indicator < PRIMARY_DRIVER_THRESHOLD and month in HARVEST_MONTHS:
            return Direction.BEARISH.value
        return Direction.NEUTRAL.value

    return Direction.NEUTRAL.value


def compute_weather_features(series: WeatherObservationSeries) -> WeatherFeatureSet:
    """Compute four deterministic features and composite direction/magnitude."""
    rainfall_deviation = compute_rainfall_deviation(series)
    rainfall_shock = compute_rainfall_shock(series)
    temperature_stress = compute_temperature_stress(series)
    harvest_risk = compute_harvest_risk_indicator(series)
    stage_weight = stage_weight_for_month(series.as_of_date.month)

    primary_driver = resolve_primary_driver(
        rainfall_deviation=rainfall_deviation,
        rainfall_shock=rainfall_shock,
        temperature_stress=temperature_stress,
        harvest_risk_indicator=harvest_risk,
        stage_weight=stage_weight,
    )

    weighted_scores = [
        abs(rainfall_deviation) * stage_weight,
        rainfall_shock * stage_weight,
        temperature_stress * stage_weight,
        harvest_risk * stage_weight,
    ]
    magnitude = clip_unit(max(weighted_scores))

    top_score = max(weighted_scores)
    direction = Direction.NEUTRAL.value
    if top_score >= PRIMARY_DRIVER_THRESHOLD:
        direction = direction_for_driver(
            primary_driver,
            rainfall_deviation=rainfall_deviation,
            rainfall_shock=rainfall_shock,
            temperature_stress=temperature_stress,
            harvest_risk_indicator=harvest_risk,
            month=series.as_of_date.month,
        )

    coverage = Decimal(series.regions_reporting) / Decimal(series.regions_expected)
    confidence = clip_unit(coverage * Decimal("0.9"))

    return WeatherFeatureSet(
        rainfall_deviation=rainfall_deviation,
        rainfall_shock=rainfall_shock,
        temperature_stress=temperature_stress,
        harvest_risk_indicator=harvest_risk,
        primary_driver=primary_driver,
        direction=direction,
        magnitude=magnitude,
        confidence=confidence,
        stage_weight=stage_weight,
        regions_reporting=series.regions_reporting,
        regions_expected=series.regions_expected,
    )
