"""Cotton v1.0.0 registry constants — TDS-009 §11.1."""

from __future__ import annotations

from datetime import date

from shared.domain.enums import AgentType, MarketRegime, ParticipantRole

COTTON_COMMODITY_ID = "cotton"
COTTON_REGISTRY_VERSION = "1.0.0"
COTTON_EFFECTIVE_FROM = date(2026, 6, 4)

COTTON_DISPLAY_NAME = "Cotton (Shankar / kapas complex)"

COTTON_PARTICIPANT_ROLES = [role.value for role in ParticipantRole]
COTTON_PHASE_1_ACTIVE_ROLES = [
    ParticipantRole.FARMER.value,
    ParticipantRole.TRADER.value,
]

COTTON_QUALITY_DIMENSIONS = [
    "grade",
    "staple_length_mm",
    "micronaire",
    "moisture_pct",
]

COTTON_REQUIRED_AGENTS = [AgentType.MARKET.value, AgentType.FUTURES.value]
COTTON_OPTIONAL_AGENTS = [
    AgentType.WEATHER.value,
    AgentType.POLICY.value,
    AgentType.DEMAND.value,
    AgentType.GLOBAL.value,
]

COTTON_SIGNAL_WEIGHTS: dict[str, float] = {
    AgentType.FUTURES.value: 0.25,
    AgentType.MARKET.value: 0.22,
    AgentType.POLICY.value: 0.15,
    AgentType.DEMAND.value: 0.15,
    AgentType.WEATHER.value: 0.13,
    AgentType.GLOBAL.value: 0.10,
}

COTTON_REGIME_PRIORITY = [regime.value for regime in MarketRegime]

COTTON_DECISION_RULES: dict[str, float | str] = {
    "msp_proximity_pct": 0.03,
    "default_partial_sell_pct": 0.50,
    "formula_version": "1.0.0",
}

COTTON_FORECAST_HORIZONS = [30, 60, 90]

COTTON_PRICE_SOURCES = ["Agmarknet", "eNAM"]
COTTON_ARRIVAL_SOURCES = ["Agmarknet"]
COTTON_DEMAND_DRIVERS = ["USDA", "ICAC"]
COTTON_POLICY_DRIVERS = ["MSP", "CCI", "PIB"]
COTTON_WEATHER_VARIABLES = ["rainfall", "humidity", "acreage"]
