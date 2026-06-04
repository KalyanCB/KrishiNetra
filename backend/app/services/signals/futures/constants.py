"""Futures signal runtime constants — E-04 F-04-05 prototype (PI10 Track A)."""

from __future__ import annotations

from decimal import Decimal
from enum import StrEnum

# Rolling window for OI z-score and near-price level (SIGNAL_ENGINE_V1 §6.2).
ROLLING_WINDOW_DAYS = 20

# Composite feature weights (registry defaults; sum <= 1).
WEIGHT_CURVE_SLOPE = 0.35
WEIGHT_BASIS = 0.30
WEIGHT_OPEN_INTEREST = 0.20
WEIGHT_CURVE_REGIME = 0.15

# Confidence baseline and prototype cap (FUTURES_SIGNAL_PROTOTYPE §7.3 G-03).
CONFIDENCE_BASE = Decimal("0.35")
CONFIDENCE_CAP_PROTOTYPE = Decimal("0.35")
FEED_FACTOR_DEGRADED = Decimal("0.35")

# Direction deadband.
DIRECTION_THRESHOLD = Decimal("0.01")
CURVE_REGIME_THRESHOLD = Decimal("0.01")

# Thin OI penalty floor (NCDEX KAPAS liquidity note, DS-001 §3).
THIN_OI_CONTRACTS = 50
THIN_OI_PENALTY = Decimal("0.15")

# Z-score normalization cap before magnitude composition.
ZSCORE_SCALE = Decimal("3.0")

AGENT_VERSION = "futures-v1.0.0-prototype"

ENVIRONMENT_PROTOTYPE = "prototype"
SOURCE_NCDEX_PUBLIC_BHAV = "ncdex_public_bhav_prototype"

# Guardrail G-02: always false for public bhav prototype path.
FUTURES_FEED_OK_PROTOTYPE = False


class CurveRegime(StrEnum):
    """Computed curve shape (dev logs only until licensed — G-07)."""

    BACKWARDATION = "backwardation"
    CONTANGO = "contango"
    FLAT = "flat"


class FuturesPrimaryDriver(StrEnum):
    """Primary driver enum for signal_components traceability."""

    CURVE_SLOPE = "curve_slope"
    BASIS = "basis"
    OPEN_INTEREST = "open_interest"
    CURVE_REGIME = "curve_regime"
