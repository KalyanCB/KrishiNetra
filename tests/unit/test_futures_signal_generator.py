"""E-04 F-04-05: FuturesSignalGenerator deterministic runtime tests."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch
from uuid import uuid4

from tests.fixtures.futures_signals import (
    AS_OF_DATE,
    FAR_SETTLE,
    NEAR_SETTLE,
    PRIMARY_MARKETS,
    SPOT_MODAL,
    kapas_curve_window,
    registry_fixture,
)

from backend.app.persistence.models.observation import ObservationValidationStatus
from backend.app.persistence.validation.signal import compute_snapshot_hash
from backend.app.services.signals.futures.constants import (
    CONFIDENCE_CAP_PROTOTYPE,
    ENVIRONMENT_PROTOTYPE,
    FUTURES_FEED_OK_PROTOTYPE,
    CurveRegime,
)
from backend.app.services.signals.futures.features import (
    classify_curve_regime,
    compute_curve_slope,
    compute_futures_features,
)
from backend.app.services.signals.futures.generator import FuturesSignalGenerator
from backend.app.services.signals.futures.observations import select_near_far_contracts
from shared.domain.enums import AgentType, Direction


def test_curve_slope_backwardation_positive() -> None:
    near = NEAR_SETTLE * Decimal("5")
    far = FAR_SETTLE * Decimal("5")
    slope = compute_curve_slope(near_settle=near, far_settle=far)
    assert slope > Decimal("0")
    assert classify_curve_regime(slope) == CurveRegime.BACKWARDATION


def test_prototype_confidence_capped() -> None:
    near = NEAR_SETTLE * Decimal("5")
    far = FAR_SETTLE * Decimal("5")
    features = compute_futures_features(
        near_settle_quintal=near,
        far_settle_quintal=far,
        spot_modal_quintal=SPOT_MODAL,
        oi_series=[30, 32, 35, 38, 40, 42],
        futures_feed_ok=False,
        confidence_base=CONFIDENCE_CAP_PROTOTYPE,
        confidence_cap=CONFIDENCE_CAP_PROTOTYPE,
        thin_oi_threshold=50,
        thin_oi_penalty_rate=Decimal("0.15"),
    )
    assert features.confidence <= CONFIDENCE_CAP_PROTOTYPE


def test_select_near_far_contracts() -> None:
    rows = kapas_curve_window()
    selected = select_near_far_contracts(rows, as_of_date=AS_OF_DATE)
    assert selected is not None
    assert selected.near.expiry_date == AS_OF_DATE.replace(day=28)
    assert selected.far.expiry_date.month == 4


@patch("backend.app.services.signals.futures.generator.RegistryService")
def test_generate_emits_four_components(mock_registry_cls: MagicMock) -> None:
    registry = registry_fixture()
    mock_registry_cls.return_value.get_active_config.return_value = registry
    generator = FuturesSignalGenerator(MagicMock())

    bundle = generator.generate(
        as_of_date=AS_OF_DATE,
        primary_market_ids=PRIMARY_MARKETS,
        futures_observations=kapas_curve_window(),
        spot_modal_quintal=SPOT_MODAL,
    )

    components = bundle.signal.signal_components or {}
    for key in FuturesSignalGenerator.EMITTED_COMPONENT_KEYS:
        assert key in components

    assert components["environment"] == ENVIRONMENT_PROTOTYPE
    assert components["futures_feed_ok"] is FUTURES_FEED_OK_PROTOTYPE
    assert components["curve_regime_mi_eligible"] is False
    assert bundle.signal.agent_type == AgentType.FUTURES
    assert bundle.features.direction in (
        Direction.BULLISH,
        Direction.BEARISH,
        Direction.NEUTRAL,
    )
    assert Decimal("0") <= bundle.signal.magnitude <= Decimal("1")
    assert Decimal("0") <= bundle.signal.confidence <= CONFIDENCE_CAP_PROTOTYPE


@patch("backend.app.services.signals.futures.generator.RegistryService")
def test_generate_replay_identical_output(mock_registry_cls: MagicMock) -> None:
    registry = registry_fixture()
    mock_registry_cls.return_value.get_active_config.return_value = registry
    generator = FuturesSignalGenerator(MagicMock())
    observations = kapas_curve_window()

    kwargs = {
        "as_of_date": AS_OF_DATE,
        "primary_market_ids": PRIMARY_MARKETS,
        "futures_observations": observations,
        "spot_modal_quintal": SPOT_MODAL,
    }
    first = generator.generate(**kwargs)
    second = generator.generate(**kwargs)

    assert first.signal.model_dump() == second.signal.model_dump()


@patch("backend.app.services.signals.futures.generator.RegistryService")
def test_generate_excludes_non_validated_observations(
    mock_registry_cls: MagicMock,
) -> None:
    registry = registry_fixture()
    mock_registry_cls.return_value.get_active_config.return_value = registry
    generator = FuturesSignalGenerator(MagicMock())

    rows = kapas_curve_window()
    rejected_id = rows[0].observation_id
    rows[0] = _futures_row(
        obs_date=rows[0].as_of_date,
        expiry_date=rows[0].expiry_date,
        settle_price=rows[0].settle_price,
        open_interest=rows[0].open_interest,
        validation_status=ObservationValidationStatus.REJECTED.value,
        observation_id=rejected_id,
    )

    bundle = generator.generate(
        as_of_date=AS_OF_DATE,
        futures_observations=rows,
        spot_modal_quintal=SPOT_MODAL,
    )
    assert rejected_id not in bundle.source_refs


def _futures_row(**kwargs):  # noqa: ANN003
    from tests.fixtures.futures_signals import _futures_row as fixture_row

    return fixture_row(**kwargs)


@patch("backend.app.services.signals.futures.generator.RegistryService")
def test_generate_and_persist_snapshot_hash_stable(mock_registry_cls: MagicMock) -> None:
    registry = registry_fixture()
    mock_registry_cls.return_value.get_active_config.return_value = registry

    session = MagicMock()
    generator = FuturesSignalGenerator(session)
    trace_id = uuid4()

    result = generator.generate_and_persist(
        as_of_date=AS_OF_DATE,
        trace_id=trace_id,
        futures_observations=kapas_curve_window(),
        spot_modal_quintal=SPOT_MODAL,
    )

    payload = {
        "agent_type": AgentType.FUTURES.value,
        "value": result.bundle.signal.value,
        "direction": result.bundle.signal.direction.value,
        "magnitude": result.bundle.signal.magnitude,
        "confidence": result.bundle.signal.confidence,
        "signal_components": result.bundle.signal.signal_components,
        "as_of_date": AS_OF_DATE,
    }
    expected_hash = compute_snapshot_hash(
        commodity_id=result.structured_signal.commodity_id,
        as_of_date=AS_OF_DATE,
        registry_id=registry.registry_id,
        signals=[payload],
        trace_id=trace_id,
    )
    assert result.snapshot.snapshot_hash == expected_hash
