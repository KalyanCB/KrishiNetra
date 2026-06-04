"""E-04-S01: MarketSignalGenerator deterministic runtime tests."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from tests.fixtures.market_signals import (
    AS_OF_DATE,
    PRIMARY_MARKETS,
    flat_arrival_window,
    mixed_validation_prices,
    registry_fixture,
    rising_price_window,
)

from backend.app.persistence.models.observation import ObservationValidationStatus
from backend.app.persistence.validation.signal import compute_snapshot_hash
from backend.app.services.signals.market.constants import (
    STUB_MSP_INR_QUINTAL,
    MarketSignalType,
)
from backend.app.services.signals.market.features import (
    arrival_season_gate,
    compute_price_momentum,
    compute_price_vs_msp_distance,
    zscore_of,
)
from backend.app.services.signals.market.generator import MarketSignalGenerator
from shared.domain.enums import AgentType, Direction


def test_zscore_deterministic() -> None:
    series = [Decimal(str(v)) for v in (6800, 6820, 6840, 6860, 6880)]
    first = zscore_of(Decimal("6880"), series)
    second = zscore_of(Decimal("6880"), series)
    assert first == second
    assert first > Decimal("0")


def test_arrival_season_gate_oct_to_mar() -> None:
    assert arrival_season_gate(date(2026, 2, 15)) == Decimal("1")
    assert arrival_season_gate(date(2026, 6, 4)) == Decimal("0")


def test_price_momentum_rising_series_bullish() -> None:
    end = AS_OF_DATE
    modals = {
        end - timedelta(days=offset): Decimal(str(6800 + 20 * (29 - offset)))
        for offset in range(30)
    }
    feature = compute_price_momentum(basket_modals=modals, as_of_date=end)
    assert feature.signal_type == MarketSignalType.PRICE_MOMENTUM
    assert feature.direction == Direction.BULLISH
    assert feature.magnitude > Decimal("0")


def test_msp_distance_uses_registry_proximity() -> None:
    feature = compute_price_vs_msp_distance(
        spot_modal=Decimal("6700"),
        msp_inr_quintal=Decimal("7121"),
        msp_proximity_pct=Decimal("0.03"),
        msp_is_stub=True,
    )
    assert feature.raw_value < Decimal("0")
    assert feature.direction == Direction.BULLISH
    assert feature.magnitude > Decimal("0")


@patch("backend.app.services.signals.market.generator.RegistryService")
def test_generate_emits_four_feature_components(mock_registry_cls: MagicMock) -> None:
    registry = registry_fixture()
    mock_registry_cls.return_value.get_active_config.return_value = registry

    prices = rising_price_window()
    arrivals = flat_arrival_window()
    generator = MarketSignalGenerator(MagicMock())

    bundle = generator.generate(
        as_of_date=AS_OF_DATE,
        primary_market_ids=PRIMARY_MARKETS,
        price_observations=prices,
        arrival_observations=arrivals,
    )

    assert len(bundle.features) == 4
    component_keys = set(bundle.signal.signal_components or {})
    for signal_type in MarketSignalGenerator.EMITTED_SIGNAL_TYPES:
        assert signal_type.value in component_keys

    assert bundle.signal.agent_type == AgentType.MARKET
    assert Decimal("0") <= bundle.signal.magnitude <= Decimal("1")
    assert Decimal("0") <= bundle.signal.confidence <= Decimal("1")
    assert bundle.msp_is_stub is True
    assert bundle.msp_inr_quintal == Decimal(str(STUB_MSP_INR_QUINTAL))


@patch("backend.app.services.signals.market.generator.RegistryService")
def test_generate_excludes_non_validated_observations(
    mock_registry_cls: MagicMock,
) -> None:
    registry = registry_fixture()
    mock_registry_cls.return_value.get_active_config.return_value = registry
    generator = MarketSignalGenerator(MagicMock())

    prices = mixed_validation_prices(days=30)
    rejected_ids = {
        row.observation_id
        for row in prices
        if row.validation_status == ObservationValidationStatus.REJECTED.value
    }

    bundle = generator.generate(
        as_of_date=AS_OF_DATE,
        primary_market_ids=PRIMARY_MARKETS,
        price_observations=prices,
        arrival_observations=[],
    )

    assert rejected_ids.isdisjoint(set(bundle.source_refs))


@patch("backend.app.services.signals.market.generator.RegistryService")
def test_generate_replay_identical_output(mock_registry_cls: MagicMock) -> None:
    registry = registry_fixture(msp_inr_quintal=7121)
    mock_registry_cls.return_value.get_active_config.return_value = registry
    generator = MarketSignalGenerator(MagicMock())

    kwargs = {
        "as_of_date": AS_OF_DATE,
        "primary_market_ids": PRIMARY_MARKETS,
        "price_observations": rising_price_window(),
        "arrival_observations": flat_arrival_window(),
    }
    first = generator.generate(**kwargs)
    second = generator.generate(**kwargs)

    assert first.signal.model_dump() == second.signal.model_dump()


@patch("backend.app.services.signals.market.generator.RegistryService")
def test_generate_and_persist_snapshot_hash_stable(mock_registry_cls: MagicMock) -> None:
    registry = registry_fixture()
    mock_registry_cls.return_value.get_active_config.return_value = registry

    session = MagicMock()
    generator = MarketSignalGenerator(session)
    trace_id = uuid4()

    prices = rising_price_window()
    arrivals = flat_arrival_window()

    result = generator.generate_and_persist(
        as_of_date=AS_OF_DATE,
        trace_id=trace_id,
        primary_market_ids=PRIMARY_MARKETS,
        price_observations=prices,
        arrival_observations=arrivals,
    )

    assert result.structured_signal.agent_type == AgentType.MARKET.value
    assert len(result.snapshot.signals) == 1
    assert result.snapshot.snapshot_hash == compute_snapshot_hash(
        commodity_id=result.structured_signal.commodity_id,
        as_of_date=AS_OF_DATE,
        registry_id=registry.registry_id,
        signals=[
            {
                "agent_type": AgentType.MARKET.value,
                "value": result.bundle.signal.value,
                "direction": result.bundle.signal.direction.value,
                "magnitude": result.bundle.signal.magnitude,
                "confidence": result.bundle.signal.confidence,
                "signal_components": result.bundle.signal.signal_components,
                "as_of_date": AS_OF_DATE,
            }
        ],
        trace_id=trace_id,
    )


def test_emitted_signal_types_constant() -> None:
    assert tuple(MarketSignalType) == MarketSignalGenerator.EMITTED_SIGNAL_TYPES
