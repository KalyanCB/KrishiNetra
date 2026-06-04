"""Market signal constants — E-04-S01 / SIGNAL_MATH_SPECIFICATION §3."""

from __future__ import annotations

from enum import StrEnum

# Rolling window for price / arrival transforms (SIGNAL_MATH §3.2).
ROLLING_WINDOW_DAYS = 30

# Z-score normalization cap before magnitude composition.
ZSCORE_SCALE = 3.0

# Composite feature weights (registry defaults; sum <= 1).
WEIGHT_PRICE_MOMENTUM = 0.35
WEIGHT_ARRIVAL_MOMENTUM = 0.25
WEIGHT_MSP_DISTANCE = 0.25
WEIGHT_PRICE_ACCELERATION = 0.15

# Confidence baseline (SIGNAL_MATH §3.5).
CONFIDENCE_BASE = 0.75
LAG_HOURS_CAP = 72.0
MAX_LAG_PENALTY = 0.30
MSP_STUB_CONFIDENCE_PENALTY = 0.10

# Phase 1 MSP stub when registry decision_rules omit msp_inr_quintal.
STUB_MSP_INR_QUINTAL = 7121

# Direction deadband for neutral classification.
DIRECTION_THRESHOLD = 0.05

# Arrival season gate FG-01: Oct–Mar inclusive.
ARRIVAL_SEASON_MONTHS = frozenset({10, 11, 12, 1, 2, 3})

AGENT_VERSION = "market-v1.0.0"


class MarketSignalType(StrEnum):
    """Four deterministic market feature signals (PI9 E-04-S01)."""

    PRICE_MOMENTUM = "price_momentum"
    ARRIVAL_MOMENTUM = "arrival_momentum"
    PRICE_VS_MSP_DISTANCE = "price_vs_msp_distance"
    PRICE_ACCELERATION = "price_acceleration"
