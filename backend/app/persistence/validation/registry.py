"""CommodityRegistry validation — ADR-003 / TDS-009 §4.1 (E-01-S10, E-02-S03)."""

from __future__ import annotations

from shared.domain.enums import AgentType

WEIGHT_SUM_TOLERANCE = 0.001
REQUIRED_FORECAST_HORIZONS = {30, 60, 90}
COTTON_REQUIRED_AGENTS = {AgentType.MARKET.value, AgentType.FUTURES.value}


class RegistryValidationError(ValueError):
    """Raised when registry config fails schema validation."""


def validate_required_agents(required_agents: list[str] | None) -> None:
    """required_agents must be non-empty and contain valid AgentType values."""
    if not required_agents:
        raise RegistryValidationError("required_agents must not be empty")

    valid = {agent.value for agent in AgentType}
    for agent in required_agents:
        if agent not in valid:
            raise RegistryValidationError(f"invalid agent type: {agent}")


def validate_optional_agents(optional_agents: list[str] | None) -> None:
    """optional_agents entries must be valid AgentType values when present."""
    if not optional_agents:
        return
    valid = {agent.value for agent in AgentType}
    for agent in optional_agents:
        if agent not in valid:
            raise RegistryValidationError(f"invalid optional agent type: {agent}")


def validate_agents_disjoint(
    required_agents: list[str] | None,
    optional_agents: list[str] | None,
) -> None:
    """required_agents and optional_agents must not overlap."""
    required = set(required_agents or [])
    optional = set(optional_agents or [])
    overlap = required & optional
    if overlap:
        raise RegistryValidationError(
            f"required_agents and optional_agents overlap: {sorted(overlap)}"
        )


def validate_signal_weights(
    signal_weights: dict[str, float] | None,
    *,
    required_agents: list[str] | None,
    optional_agents: list[str] | None,
) -> None:
    """signal_weights keys must be subset of agents and sum to 1.0 ± tolerance."""
    if not signal_weights:
        raise RegistryValidationError("signal_weights must not be empty")

    allowed = set(required_agents or []) | set(optional_agents or [])
    invalid_keys = set(signal_weights) - allowed
    if invalid_keys:
        raise RegistryValidationError(
            f"signal_weights contains unknown agents: {sorted(invalid_keys)}"
        )

    total = sum(signal_weights.values())
    if abs(total - 1.0) > WEIGHT_SUM_TOLERANCE:
        raise RegistryValidationError(
            f"signal_weights must sum to 1.0 ± {WEIGHT_SUM_TOLERANCE}, got {total}"
        )


def validate_forecast_horizons(forecast_horizons: list[int] | None) -> None:
    """forecast_horizons must include 30, 60, 90 (REQ-076)."""
    if not forecast_horizons:
        raise RegistryValidationError("forecast_horizons must not be empty")
    missing = REQUIRED_FORECAST_HORIZONS - set(forecast_horizons)
    if missing:
        raise RegistryValidationError(
            f"forecast_horizons missing required values: {sorted(missing)}"
        )


def validate_decision_rules(decision_rules: dict | None) -> None:
    """decision_rules must include ADR-003 required keys."""
    if not decision_rules:
        raise RegistryValidationError("decision_rules must not be empty")
    required_keys = {"msp_proximity_pct", "default_partial_sell_pct", "formula_version"}
    missing = required_keys - set(decision_rules)
    if missing:
        raise RegistryValidationError(f"decision_rules missing keys: {sorted(missing)}")


def validate_cotton_required_agents(required_agents: list[str] | None) -> None:
    """Cotton registry must include Market and Futures (TDS-009 §11.1)."""
    if not required_agents:
        raise RegistryValidationError("required_agents must not be empty")
    missing = COTTON_REQUIRED_AGENTS - set(required_agents)
    if missing:
        raise RegistryValidationError(
            f"cotton required_agents missing: {sorted(missing)}"
        )


def validate_registry_config(
    *,
    required_agents: list[str] | None,
    optional_agents: list[str] | None = None,
    signal_weights: dict[str, float] | None = None,
    forecast_horizons: list[int] | None = None,
    decision_rules: dict | None = None,
    commodity_id: str | None = None,
) -> None:
    """Validate registry fields before insert or activation."""
    validate_required_agents(required_agents)
    validate_optional_agents(optional_agents)
    validate_agents_disjoint(required_agents, optional_agents)
    validate_decision_rules(decision_rules)
    if signal_weights is not None:
        validate_signal_weights(
            signal_weights,
            required_agents=required_agents,
            optional_agents=optional_agents,
        )
    if forecast_horizons is not None:
        validate_forecast_horizons(forecast_horizons)
    if commodity_id == "cotton":
        validate_cotton_required_agents(required_agents)
