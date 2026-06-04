"""CommodityRegistry validation — ADR-003 / TDS-009 §4.1 (E-01-S10)."""

from __future__ import annotations

from shared.domain.enums import AgentType


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


def validate_decision_rules(decision_rules: dict | None) -> None:
    """decision_rules must include ADR-003 required keys."""
    if not decision_rules:
        raise RegistryValidationError("decision_rules must not be empty")
    required_keys = {"msp_proximity_pct", "default_partial_sell_pct", "formula_version"}
    missing = required_keys - set(decision_rules)
    if missing:
        raise RegistryValidationError(
            f"decision_rules missing keys: {sorted(missing)}"
        )


def validate_registry_config(
    *,
    required_agents: list[str] | None,
    optional_agents: list[str] | None = None,
    decision_rules: dict | None = None,
) -> None:
    """Validate registry fields before insert or activation."""
    validate_required_agents(required_agents)
    validate_optional_agents(optional_agents)
    validate_decision_rules(decision_rules)
