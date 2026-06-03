"""Domain enums aligned to TDS-004, TDS-006, TDS-009, TDS-013 §5.2."""

from __future__ import annotations

from enum import StrEnum


class AgentType(StrEnum):
    """TDS-004 §3 domain agents (includes Global)."""

    MARKET = "Market"
    WEATHER = "Weather"
    POLICY = "Policy"
    DEMAND = "Demand"
    FUTURES = "Futures"
    GLOBAL = "Global"


class Direction(StrEnum):
    """TDS-004 signal direction."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class ActionType(StrEnum):
    """TDS-013 §5.2 decision actions."""

    SELL = "SELL"
    HOLD = "HOLD"
    PARTIAL_SELL = "PARTIAL_SELL"
    PARTIAL_HOLD = "PARTIAL_HOLD"


class PersonaType(StrEnum):
    """TDS-002 / TDS-006 UserContext persona_type."""

    FARMER = "farmer"
    TRADER = "trader"


class LiquidityNeed(StrEnum):
    """TDS-006 UserContext liquidity_need severity."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class MarketRegime(StrEnum):
    """TDS-009 regime_priority ordering (subset for Phase 1)."""

    DATA_DEGRADED = "DATA_DEGRADED"
    MSP_FLOOR = "MSP_FLOOR"
    CURVE_BACKWARDATION = "CURVE_BACKWARDATION"
    TIGHT_SUPPLY = "TIGHT_SUPPLY"
    EXPORT_PUSH = "EXPORT_PUSH"
    NORMAL = "NORMAL"


class CommodityType(StrEnum):
    """Phase 1 commodities (TDS-006 Commodity root)."""

    COTTON = "cotton"


class EventType(StrEnum):
    """TDS-005 business event catalog (names only; no schemas)."""

    PRICE_UPDATED = "PRICE_UPDATED"
    ARRIVAL_UPDATED = "ARRIVAL_UPDATED"
    WEATHER_UPDATED = "WEATHER_UPDATED"
    POLICY_UPDATED = "POLICY_UPDATED"
    DEMAND_SIGNAL_UPDATED = "DEMAND_SIGNAL_UPDATED"
    FUTURES_SIGNAL_UPDATED = "FUTURES_SIGNAL_UPDATED"
    GLOBAL_SIGNAL_UPDATED = "GLOBAL_SIGNAL_UPDATED"
    FORECAST_GENERATED = "FORECAST_GENERATED"
    MI_SNAPSHOT_READY = "MI_SNAPSHOT_READY"
    DECISION_REQUESTED = "DECISION_REQUESTED"
    RECOMMENDATION_GENERATED = "RECOMMENDATION_GENERATED"
    EXPLANATION_GENERATED = "EXPLANATION_GENERATED"
    OUTCOME_CAPTURED = "OUTCOME_CAPTURED"
    DATA_REFRESH_STARTED = "DATA_REFRESH_STARTED"
    DATA_REFRESH_COMPLETED = "DATA_REFRESH_COMPLETED"
