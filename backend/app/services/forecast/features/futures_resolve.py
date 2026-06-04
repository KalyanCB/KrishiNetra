"""Resolve Futures inputs for forecast feature assembly — PI10 Track C."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.app.persistence.models.signal import StructuredSignalModel
from backend.app.services.forecast.features.futures_stub import (
    FuturesSignalStub,
    build_futures_signal_stub,
)
from backend.app.services.registry.service import RegistryNotFoundError, RegistryService
from backend.app.services.signals.futures.constants import AGENT_VERSION
from backend.app.services.signals.futures.generator import (
    FuturesSignalBundle,
    FuturesSignalGenerator,
)
from shared.domain.enums import AgentType


def structured_signal_model_from_bundle(
    *,
    bundle: FuturesSignalBundle,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    trace_id: UUID | None = None,
) -> StructuredSignalModel:
    """Build ephemeral StructuredSignalModel from generator output (not persisted)."""
    signal = bundle.signal
    return StructuredSignalModel(
        signal_id=uuid4(),
        agent_type=AgentType.FUTURES.value,
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        as_of_timestamp=signal.as_of_timestamp,
        value=signal.value,
        direction=signal.direction.value,
        magnitude=signal.magnitude,
        confidence=signal.confidence,
        signal_components=signal.signal_components,
        source_observation_refs=[str(ref) for ref in bundle.source_refs],
        registry_id=registry_id,
        agent_version=AGENT_VERSION,
        trace_id=trace_id,
    )


def resolve_futures_input(
    *,
    session: Session | None,
    commodity_id: str,
    as_of_date: date,
    futures: StructuredSignalModel | None,
    use_futures_stub: bool,
) -> StructuredSignalModel | FuturesSignalStub | None:
    """
    Prefer explicit futures row, then FuturesSignalGenerator when session is set,
    else deterministic stub when ``use_futures_stub`` is True.
    """
    if futures is not None:
        return futures
    if session is not None:
        try:
            registry = RegistryService(session).get_active_config(commodity_id)
        except RegistryNotFoundError:
            if use_futures_stub:
                return build_futures_signal_stub(as_of_date=as_of_date)
            return None
        bundle = FuturesSignalGenerator(session).generate(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
        )
        return structured_signal_model_from_bundle(
            bundle=bundle,
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry.registry_id,
        )
    if use_futures_stub:
        return build_futures_signal_stub(as_of_date=as_of_date)
    return None
