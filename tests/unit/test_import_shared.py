"""E-00-S02: Editable install smoke tests."""

from __future__ import annotations


def test_import_shared_package() -> None:
    import shared  # noqa: F401
    from shared.domain import AgentType, CommodityType, EventType
    from shared.signal_contract import StructuredSignal

    assert AgentType.MARKET.value == "Market"
    assert CommodityType.COTTON.value == "cotton"
    assert EventType.PRICE_UPDATED.value == "PRICE_UPDATED"
    assert StructuredSignal.__name__ == "StructuredSignal"


def test_import_backend_app_package() -> None:
    import backend.app  # noqa: F401


def test_import_global_signals_agent_package() -> None:
    """ADR-005: Global Agent lives under agents.global_signals."""
    import agents.global_signals  # noqa: F401


def test_domain_packages_importable() -> None:
    import agents  # noqa: F401
    import decision_engine  # noqa: F401
    import forecasting  # noqa: F401
    import market_intelligence  # noqa: F401
