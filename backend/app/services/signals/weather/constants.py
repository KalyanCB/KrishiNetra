"""Weather signal runtime constants — Telangana cotton belt (E-04-S02)."""

from __future__ import annotations

from decimal import Decimal

from backend.app.services.ingest.weather.constants import DISTRICT_REGION_IDS

# Five TG belt regions with NASA POWER backfill (WEATHER_DATA_STRATEGY_V1 §4).
TELANGANA_WEATHER_REGION_IDS: tuple[str, ...] = tuple(DISTRICT_REGION_IDS.values())

LOOKBACK_DAYS = 30
CLIMATOLOGY_DAYS = 365

# Feature thresholds (SIGNAL_MATH §4 — primary_driver gate).
PRIMARY_DRIVER_THRESHOLD = Decimal("0.15")

# Temperature stress reference (NASA POWER T2M daily mean).
TEMPERATURE_OPTIMAL_C = Decimal("28")
TEMPERATURE_STRESS_BAND_C = Decimal("10")

# Rainfall shock denominator floor (mm/day regional mean).
RAINFALL_SHOCK_FLOOR_MM = Decimal("5")

# Harvest risk rain reference (7d regional sum, mm).
HARVEST_RAIN_7D_REFERENCE_MM = Decimal("80")

# Lifecycle stage weights (COTTON_LIFECYCLE_SIGNAL_MAPPING §6).
STAGE_WEIGHT_HIGH = Decimal("1.0")
STAGE_WEIGHT_MEDIUM = Decimal("0.6")
STAGE_WEIGHT_LOW = Decimal("0.3")

AGENT_VERSION = "weather_signal_v1.0.0"

# Component keys persisted in signal_components (E-04-S02 charter).
RAINFALL_DEVIATION = "rainfall_deviation"
RAINFALL_SHOCK = "rainfall_shock"
TEMPERATURE_STRESS = "temperature_stress"
HARVEST_RISK_INDICATOR = "harvest_risk_indicator"
PRIMARY_DRIVER = "primary_driver"
