"""Assemble forecast feature values and lineage from agent signals — PI10 Track C."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.persistence.models.signal import StructuredSignalModel
from backend.app.persistence.validation.forecast_features import ASSEMBLY_VERSION
from backend.app.services.forecast.features.futures_resolve import resolve_futures_input
from backend.app.services.forecast.features.futures_stub import (
    FuturesSignalStub,
    structured_signal_lineage_entry,
)
from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID
from shared.domain.enums import AgentType

_AGENT_PREFIX = {
    AgentType.MARKET.value: "market",
    AgentType.WEATHER.value: "weather",
    AgentType.FUTURES.value: "futures",
}


def _decimal_value(value: Decimal | float | int | str) -> float | int | str:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _agent_prefix(agent_type: str) -> str:
    return _AGENT_PREFIX.get(agent_type, agent_type.lower())


def features_from_structured_signal(signal: StructuredSignalModel) -> dict[str, Any]:
    """Project one StructuredSignal into namespaced flat feature map."""
    prefix = _agent_prefix(signal.agent_type)
    values: dict[str, Any] = {
        f"{prefix}.direction": signal.direction,
        f"{prefix}.magnitude": _decimal_value(signal.magnitude),
        f"{prefix}.confidence": _decimal_value(signal.confidence),
        f"{prefix}.value": _decimal_value(signal.value),
    }
    components = signal.signal_components or {}
    for key, raw in sorted(components.items()):
        if isinstance(raw, (Decimal, float, int, str, bool)) or raw is None:
            values[f"{prefix}.components.{key}"] = (
                _decimal_value(raw) if isinstance(raw, Decimal) else raw
            )
        else:
            values[f"{prefix}.components.{key}"] = raw
    return values


def features_from_futures_stub(stub: FuturesSignalStub) -> dict[str, Any]:
    """Project stub Futures row into namespaced flat feature map."""
    prefix = _agent_prefix(stub.agent_type)
    values: dict[str, Any] = {
        f"{prefix}.direction": stub.direction,
        f"{prefix}.magnitude": _decimal_value(stub.magnitude),
        f"{prefix}.confidence": _decimal_value(stub.confidence),
        f"{prefix}.value": _decimal_value(stub.value),
        f"{prefix}.stub": True,
    }
    for key, raw in sorted(stub.signal_components.items()):
        if isinstance(raw, (Decimal, float, int, str, bool)) or raw is None:
            values[f"{prefix}.components.{key}"] = (
                _decimal_value(raw) if isinstance(raw, Decimal) else raw
            )
        else:
            values[f"{prefix}.components.{key}"] = raw
    return values


def lineage_from_signals(
    *,
    market: StructuredSignalModel | None,
    weather: StructuredSignalModel | None,
    futures: StructuredSignalModel | FuturesSignalStub | None,
    snapshot_trace_id: UUID | None = None,
) -> dict[str, object]:
    """Record agent provenance for replay and audit."""
    agents: dict[str, object] = {}
    if market is not None:
        agents[AgentType.MARKET.value] = structured_signal_lineage_entry(
            signal_id=market.signal_id,
            agent_type=market.agent_type,
            agent_version=market.agent_version,
            trace_id=market.trace_id,
        )
    if weather is not None:
        agents[AgentType.WEATHER.value] = structured_signal_lineage_entry(
            signal_id=weather.signal_id,
            agent_type=weather.agent_type,
            agent_version=weather.agent_version,
            trace_id=weather.trace_id,
        )
    if futures is not None:
        if isinstance(futures, FuturesSignalStub):
            agents[AgentType.FUTURES.value] = futures.to_lineage_entry()
        else:
            agents[AgentType.FUTURES.value] = structured_signal_lineage_entry(
                signal_id=futures.signal_id,
                agent_type=futures.agent_type,
                agent_version=futures.agent_version,
                trace_id=futures.trace_id,
            )

    lineage: dict[str, object] = {
        "assembly_version": ASSEMBLY_VERSION,
        "agents": agents,
    }
    if snapshot_trace_id is not None:
        lineage["snapshot_trace_id"] = str(snapshot_trace_id)
    return lineage


def assemble_forecast_features(
    *,
    as_of_date: date,
    market: StructuredSignalModel | None,
    weather: StructuredSignalModel | None,
    futures: StructuredSignalModel | None = None,
    session: Session | None = None,
    commodity_id: str = COTTON_COMMODITY_ID,
    use_futures_stub: bool = True,
    snapshot_trace_id: UUID | None = None,
) -> tuple[dict[str, Any], dict[str, object]]:
    """
    Build feature_values map and feature_lineage from Market, Weather, Futures inputs.

    When ``futures`` is omitted and ``session`` is provided, ``FuturesSignalGenerator``
    supplies a deterministic prototype row. Without session, a neutral stub is used
    when ``use_futures_stub`` is True.
    """
    futures_input = resolve_futures_input(
        session=session,
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        futures=futures,
        use_futures_stub=use_futures_stub,
    )

    values: dict[str, Any] = {}
    if market is not None:
        values.update(features_from_structured_signal(market))
    if weather is not None:
        values.update(features_from_structured_signal(weather))
    if futures_input is not None:
        if isinstance(futures_input, FuturesSignalStub):
            values.update(features_from_futures_stub(futures_input))
        else:
            values.update(features_from_structured_signal(futures_input))

    lineage = lineage_from_signals(
        market=market,
        weather=weather,
        futures=futures_input,
        snapshot_trace_id=snapshot_trace_id,
    )
    return values, lineage
