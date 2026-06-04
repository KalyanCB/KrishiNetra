"""PI9 Track D — Same Inputs = Same Outputs replay harness (Tracks A/B/C)."""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.app.persistence.models.signal import (
    SignalSnapshotModel,
    StructuredSignalModel,
)
from backend.app.persistence.repositories.signal import SignalSnapshotRepository
from backend.app.persistence.validation.signal import (
    PI9_SIGNAL_TYPE,
    compute_snapshot_hash,
    structured_signal_to_persisted_row,
)
from backend.app.services.signals.market.generator import (
    MarketSignalBundle,
    MarketSignalGenerator,
    MarketSignalPersistResult,
)
from backend.app.services.signals.weather.generator import WeatherSignalGenerator
from shared.domain.enums import AgentType

DEFAULT_REPLAY_CYCLES = 5

STRUCTURED_COMPARE_KEYS: tuple[str, ...] = (
    "agent_type",
    "commodity_id",
    "as_of_date",
    "value",
    "direction",
    "magnitude",
    "confidence",
    "signal_components",
    "source_observation_refs",
    "agent_version",
)


def _decimal_str(value: Decimal | float | int | str) -> str:
    if isinstance(value, Decimal):
        return str(value)
    return str(Decimal(str(value)))


def structured_signal_comparable(entity: StructuredSignalModel) -> dict[str, Any]:
    """Project StructuredSignal to a stable, UUID-free comparison dict."""
    refs = entity.source_observation_refs or []
    return {
        "agent_type": entity.agent_type,
        "commodity_id": entity.commodity_id,
        "as_of_date": entity.as_of_date.isoformat(),
        "value": _decimal_str(entity.value),
        "direction": entity.direction,
        "magnitude": _decimal_str(entity.magnitude),
        "confidence": _decimal_str(entity.confidence),
        "signal_components": entity.signal_components or {},
        "source_observation_refs": sorted(str(ref) for ref in refs),
        "agent_version": entity.agent_version,
    }


def market_snapshot_payload(
    result: MarketSignalPersistResult,
    *,
    as_of_date: date,
) -> dict[str, object]:
    """Build Track C payload for Market signal snapshot insertion."""
    signal = result.bundle.signal
    return {
        "agent_type": AgentType.MARKET.value,
        "value": signal.value,
        "direction": signal.direction.value,
        "magnitude": signal.magnitude,
        "confidence": signal.confidence,
        "signal_components": signal.signal_components,
        "as_of_date": as_of_date,
    }


def weather_snapshot_payload(signal: StructuredSignalModel) -> dict[str, object]:
    """Build Track C payload for Weather signal snapshot insertion."""
    return {
        "agent_type": AgentType.WEATHER.value,
        "value": signal.value,
        "direction": signal.direction,
        "magnitude": signal.magnitude,
        "confidence": signal.confidence,
        "signal_components": signal.signal_components,
        "as_of_date": signal.as_of_date,
    }


@dataclass(frozen=True, slots=True)
class GeneratorReplayFingerprint:
    """Comparable output for one generator cycle (Track A or B)."""

    track: str
    structured: dict[str, Any]
    signal_row: dict[str, Any]
    snapshot_hash: str | None = None


@dataclass(frozen=True, slots=True)
class CombinedSnapshotFingerprint:
    """Track C SignalSnapshot contract — hash + PI9 JSONB rows."""

    snapshot_hash: str
    signals: tuple[dict[str, Any], ...]
    market_structured: dict[str, Any]
    weather_structured: dict[str, Any]


@dataclass(frozen=True, slots=True)
class ReplayValidationResult:
    """Outcome of multi-cycle replay validation."""

    track: str
    cycles_requested: int
    cycles_run: int
    passed: bool
    baseline_fingerprint: str
    mismatches: tuple[str, ...]


def fingerprint_to_json(fingerprint: object) -> str:
    """Stable JSON for cross-cycle equality checks."""
    return json.dumps(fingerprint, sort_keys=True, separators=(",", ":"), default=str)


def _market_structured_from_bundle(
    bundle: MarketSignalBundle,
    *,
    commodity_id: str,
    as_of_date: date,
) -> dict[str, Any]:
    signal = bundle.signal
    return {
        "agent_type": signal.agent_type.value,
        "commodity_id": commodity_id,
        "as_of_date": as_of_date.isoformat(),
        "value": _decimal_str(signal.value),
        "direction": signal.direction.value,
        "magnitude": _decimal_str(signal.magnitude),
        "confidence": _decimal_str(signal.confidence),
        "signal_components": signal.signal_components or {},
        "source_observation_refs": sorted(str(ref) for ref in bundle.source_refs),
        "agent_version": None,
    }


def _market_signal_row_from_bundle(
    bundle: MarketSignalBundle,
    *,
    as_of_date: date,
) -> dict[str, Any]:
    signal = bundle.signal
    return structured_signal_to_persisted_row(
        StructuredSignalModel(
            signal_id=UUID(int=0),
            agent_type=signal.agent_type.value,
            commodity_id=signal.commodity_id.value,
            as_of_date=as_of_date,
            as_of_timestamp=signal.as_of_timestamp,
            value=signal.value,
            direction=signal.direction.value,
            magnitude=signal.magnitude,
            confidence=signal.confidence,
            signal_components=signal.signal_components,
            registry_id=UUID(int=0),
        )
    )


def fingerprint_market_bundle(
    bundle: MarketSignalBundle,
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    trace_id: UUID,
) -> GeneratorReplayFingerprint:
    """Fingerprint Market generate() output including snapshot_hash."""
    payload = {
        "agent_type": AgentType.MARKET.value,
        "value": bundle.signal.value,
        "direction": bundle.signal.direction.value,
        "magnitude": bundle.signal.magnitude,
        "confidence": bundle.signal.confidence,
        "signal_components": bundle.signal.signal_components,
        "as_of_date": as_of_date,
    }
    snapshot_hash = compute_snapshot_hash(
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry_id=registry_id,
        signals=[payload],
        trace_id=trace_id,
    )
    return GeneratorReplayFingerprint(
        track="market",
        structured=_market_structured_from_bundle(
            bundle, commodity_id=commodity_id, as_of_date=as_of_date
        ),
        signal_row=_market_signal_row_from_bundle(bundle, as_of_date=as_of_date),
        snapshot_hash=snapshot_hash,
    )


def fingerprint_market_cycle(
    result: MarketSignalPersistResult,
    *,
    as_of_date: date,
    registry_id: UUID,
    trace_id: UUID,
) -> GeneratorReplayFingerprint:
    """Fingerprint Market generator output including snapshot_hash."""
    payload = market_snapshot_payload(result, as_of_date=as_of_date)
    snapshot_hash = compute_snapshot_hash(
        commodity_id=result.structured_signal.commodity_id,
        as_of_date=as_of_date,
        registry_id=registry_id,
        signals=[payload],
        trace_id=trace_id,
    )
    return GeneratorReplayFingerprint(
        track="market",
        structured=structured_signal_comparable(result.structured_signal),
        signal_row=structured_signal_to_persisted_row(result.structured_signal),
        snapshot_hash=snapshot_hash,
    )


def fingerprint_weather_cycle(
    signal: StructuredSignalModel,
) -> GeneratorReplayFingerprint:
    """Fingerprint Weather generator output (no snapshot until assembly)."""
    return GeneratorReplayFingerprint(
        track="weather",
        structured=structured_signal_comparable(signal),
        signal_row=structured_signal_to_persisted_row(signal),
        snapshot_hash=None,
    )


def fingerprint_combined_snapshot(
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    trace_id: UUID,
    market: MarketSignalPersistResult,
    weather: StructuredSignalModel,
) -> CombinedSnapshotFingerprint:
    """Fingerprint Track C combined Market + Weather SignalSnapshot (persist path)."""
    return fingerprint_combined_snapshot_from_signals(
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry_id=registry_id,
        trace_id=trace_id,
        market_bundle=market.bundle,
        weather=weather,
    )


def fingerprint_combined_snapshot_from_signals(
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    trace_id: UUID,
    market_bundle: MarketSignalBundle,
    weather: StructuredSignalModel,
) -> CombinedSnapshotFingerprint:
    """Fingerprint Track C snapshot from generate() outputs (no DB writes)."""
    payloads = [
        {
            "agent_type": AgentType.MARKET.value,
            "value": market_bundle.signal.value,
            "direction": market_bundle.signal.direction.value,
            "magnitude": market_bundle.signal.magnitude,
            "confidence": market_bundle.signal.confidence,
            "signal_components": market_bundle.signal.signal_components,
            "as_of_date": as_of_date,
        },
        weather_snapshot_payload(weather),
    ]
    snapshot_hash = compute_snapshot_hash(
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry_id=registry_id,
        signals=payloads,
        trace_id=trace_id,
    )
    normalized = sorted(
        [
            _market_signal_row_from_bundle(market_bundle, as_of_date=as_of_date),
            structured_signal_to_persisted_row(weather),
        ],
        key=lambda row: row[PI9_SIGNAL_TYPE],
    )
    return CombinedSnapshotFingerprint(
        snapshot_hash=snapshot_hash,
        signals=tuple(normalized),
        market_structured=_market_structured_from_bundle(
            market_bundle, commodity_id=commodity_id, as_of_date=as_of_date
        ),
        weather_structured=structured_signal_comparable(weather),
    )


def assemble_combined_snapshot(
    session: Session,
    *,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    trace_id: UUID,
    market: MarketSignalPersistResult,
    weather: StructuredSignalModel,
    data_quality_snapshot_id: UUID | None = None,
) -> SignalSnapshotModel:
    """Persist combined Market + Weather snapshot via Track C repository."""
    payloads = [
        market_snapshot_payload(market, as_of_date=as_of_date),
        weather_snapshot_payload(weather),
    ]
    snapshot = SignalSnapshotModel(
        snapshot_id=uuid4(),
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry_id=registry_id,
        signal_ids=[
            str(market.structured_signal.signal_id),
            str(weather.signal_id),
        ],
        snapshot_hash="",
        trace_id=trace_id,
        data_quality_snapshot_id=data_quality_snapshot_id,
    )
    repo = SignalSnapshotRepository(session)
    return repo.insert_snapshot(snapshot, signal_payloads=payloads)


def validate_replay_cycles(
    *,
    track: str,
    cycles: int,
    runner: Callable[[], object],
) -> ReplayValidationResult:
    """
    Run ``runner`` ``cycles`` times; all fingerprints must match cycle 0.

    ``runner`` returns GeneratorReplayFingerprint or CombinedSnapshotFingerprint.
    """
    if cycles < 1:
        raise ValueError("cycles must be >= 1")

    fingerprints: list[str] = []
    mismatches: list[str] = []

    for index in range(cycles):
        fingerprint = runner()
        encoded = fingerprint_to_json(fingerprint)
        fingerprints.append(encoded)
        if index > 0 and encoded != fingerprints[0]:
            mismatches.append(f"cycle_{index}_diverged_from_baseline")

    return ReplayValidationResult(
        track=track,
        cycles_requested=cycles,
        cycles_run=len(fingerprints),
        passed=len(mismatches) == 0,
        baseline_fingerprint=fingerprints[0] if fingerprints else "",
        mismatches=tuple(mismatches),
    )


def run_market_replay(
    generator: MarketSignalGenerator,
    *,
    cycles: int = DEFAULT_REPLAY_CYCLES,
    commodity_id: str,
    as_of_date: date,
    trace_id: UUID,
    registry_id: UUID,
    primary_market_ids: tuple[str, ...] | None = None,
    price_observations: list[object] | None = None,
    arrival_observations: list[object] | None = None,
) -> ReplayValidationResult:
    """Validate MarketSignalGenerator produces identical output across cycles."""

    def _cycle() -> GeneratorReplayFingerprint:
        bundle = generator.generate(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            primary_market_ids=primary_market_ids,
            price_observations=price_observations,  # type: ignore[arg-type]
            arrival_observations=arrival_observations,  # type: ignore[arg-type]
        )
        return fingerprint_market_bundle(
            bundle,
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry_id,
            trace_id=trace_id,
        )

    return validate_replay_cycles(track="market", cycles=cycles, runner=_cycle)


def run_weather_replay(
    generator: WeatherSignalGenerator,
    *,
    cycles: int = DEFAULT_REPLAY_CYCLES,
    commodity_id: str,
    as_of_date: date,
    registry_id: UUID,
    trace_id: UUID | None = None,
    source: str | None = None,
    as_of_timestamp: object | None = None,
) -> ReplayValidationResult:
    """Validate WeatherSignalGenerator produces identical output across cycles."""

    def _cycle() -> GeneratorReplayFingerprint:
        signal = generator.generate(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry_id,
            trace_id=trace_id,
            source=source,
            as_of_timestamp=as_of_timestamp,  # type: ignore[arg-type]
        )
        return fingerprint_weather_cycle(signal)

    return validate_replay_cycles(track="weather", cycles=cycles, runner=_cycle)


def summarize_results(results: Sequence[ReplayValidationResult]) -> dict[str, Any]:
    """Aggregate replay outcomes for reporting."""
    return {
        "cycles_requested": results[0].cycles_requested if results else 0,
        "tracks": [
            {
                "track": result.track,
                "cycles_run": result.cycles_run,
                "passed": result.passed,
                "mismatches": list(result.mismatches),
            }
            for result in results
        ],
        "all_passed": all(result.passed for result in results),
    }
