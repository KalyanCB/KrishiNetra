"""E-02-S03: CommodityRegistry config validation tests."""

from __future__ import annotations

import pytest

from backend.app.persistence.validation.registry import (
    RegistryValidationError,
    validate_agents_disjoint,
    validate_cotton_required_agents,
    validate_decision_rules,
    validate_forecast_horizons,
    validate_registry_config,
    validate_signal_weights,
)


def _valid_config() -> dict:
    return {
        "required_agents": ["Market", "Futures"],
        "optional_agents": ["Weather", "Policy", "Demand", "Global"],
        "signal_weights": {
            "Futures": 0.25,
            "Market": 0.22,
            "Policy": 0.15,
            "Demand": 0.15,
            "Weather": 0.13,
            "Global": 0.10,
        },
        "forecast_horizons": [30, 60, 90],
        "decision_rules": {
            "msp_proximity_pct": 0.03,
            "default_partial_sell_pct": 0.50,
            "formula_version": "1.0.0",
        },
    }


def test_weights_sum_to_one() -> None:
    cfg = _valid_config()
    cfg["signal_weights"]["Market"] = 0.05
    with pytest.raises(RegistryValidationError, match="sum to 1.0"):
        validate_signal_weights(
            cfg["signal_weights"],
            required_agents=cfg["required_agents"],
            optional_agents=cfg["optional_agents"],
        )


def test_required_agents_disjoint_optional() -> None:
    with pytest.raises(RegistryValidationError, match="overlap"):
        validate_agents_disjoint(["Market", "Futures"], ["Market", "Weather"])


def test_cotton_decision_rules_defaults() -> None:
    rules = {
        "msp_proximity_pct": 0.03,
        "default_partial_sell_pct": 0.50,
        "formula_version": "1.0.0",
    }
    validate_decision_rules(rules)
    assert rules["msp_proximity_pct"] == 0.03
    assert rules["default_partial_sell_pct"] == 0.50


def test_forecast_horizons_required() -> None:
    with pytest.raises(RegistryValidationError, match="missing required"):
        validate_forecast_horizons([30, 60])


def test_cotton_required_agents_missing_futures() -> None:
    with pytest.raises(RegistryValidationError, match="missing"):
        validate_cotton_required_agents(["Market"])


def test_full_registry_config_valid() -> None:
    cfg = _valid_config()
    validate_registry_config(commodity_id="cotton", **cfg)


def test_registry_config_rejects_invalid_agent_in_weights() -> None:
    cfg = _valid_config()
    cfg["signal_weights"]["Invalid"] = 0.0
    with pytest.raises(RegistryValidationError, match="unknown agents"):
        validate_registry_config(commodity_id="cotton", **cfg)
