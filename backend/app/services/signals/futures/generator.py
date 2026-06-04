"""FuturesSignalGenerator — E-04 F-04-05 deterministic prototype runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.app.persistence.models.futures import FuturesObservationModel
from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.models.signal import (
    SignalSnapshotModel,
    StructuredSignalModel,
)
from backend.app.persistence.repositories.quality import DataQualitySnapshotRepository
from backend.app.persistence.repositories.signal import (
    SignalSnapshotRepository,
    StructuredSignalRepository,
)
from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_telangana_primary_market_ids,
)
from backend.app.services.registry.service import RegistryService
from backend.app.services.signals.common import signed_value
from backend.app.services.signals.futures.constants import (
    AGENT_VERSION,
    CONFIDENCE_BASE,
    CONFIDENCE_CAP_PROTOTYPE,
    ENVIRONMENT_PROTOTYPE,
    FUTURES_FEED_OK_PROTOTYPE,
    SOURCE_NCDEX_PUBLIC_BHAV,
    THIN_OI_CONTRACTS,
    THIN_OI_PENALTY,
)
from backend.app.services.signals.futures.features import (
    FuturesFeatureSet,
    compute_futures_features,
)
from backend.app.services.signals.futures.observations import (
    FuturesObservationSeries,
    load_observation_series,
    load_spot_modal_quintal,
)
from shared.domain.enums import AgentType, CommodityType
from shared.signal_contract.models import StructuredSignal


@dataclass(frozen=True, slots=True)
class FuturesSignalBundle:
    """Feature set plus composite StructuredSignal contract."""

    features: FuturesFeatureSet
    signal: StructuredSignal
    source_refs: tuple[UUID, ...]
    environment: str
    futures_feed_ok: bool


@dataclass(frozen=True, slots=True)
class FuturesSignalPersistResult:
    """Outcome of generate_and_persist."""

    bundle: FuturesSignalBundle
    structured_signal: StructuredSignalModel
    snapshot: SignalSnapshotModel


class FuturesSignalGenerator:
    """
    Deterministic Futures agent runtime (SIGNAL_ENGINE_V1 §6).

    Prototype path: NCDEX public bhav observations only; confidence capped ≤ 0.35;
    futures_feed_ok=false per FUTURES_SIGNAL_PROTOTYPE §7.3 guardrails.
    """

    EMITTED_COMPONENT_KEYS: tuple[str, ...] = (
        "curve_slope",
        "basis_futures_spot",
        "open_interest_change",
        "curve_regime",
    )

    def __init__(self, session: Session) -> None:
        self._session = session
        self._signal_repo = StructuredSignalRepository(session)
        self._snapshot_repo = SignalSnapshotRepository(session)
        self._quality_repo = DataQualitySnapshotRepository(session)
        self._registry = RegistryService(session)

    def generate(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        as_of_date: date,
        primary_market_ids: tuple[str, ...] | None = None,
        observation_series: FuturesObservationSeries | None = None,
        spot_modal_quintal: Decimal | None = None,
        quality_snapshot: DataQualitySnapshotModel | None = None,
        source: str = SOURCE_NCDEX_PUBLIC_BHAV,
        futures_observations: list[FuturesObservationModel] | None = None,
    ) -> FuturesSignalBundle:
        """Compute futures feature signals and composite StructuredSignal."""
        registry = self._registry.get_active_config(commodity_id)
        markets = primary_market_ids or load_telangana_primary_market_ids()

        if observation_series is None and futures_observations is not None:
            observation_series = _series_from_injected(
                futures_observations,
                as_of_date=as_of_date,
            )
        if observation_series is None:
            observation_series = load_observation_series(
                self._session,
                commodity_id=commodity_id,
                as_of_date=as_of_date,
                source=source,
            )
        if spot_modal_quintal is None:
            spot_modal_quintal = load_spot_modal_quintal(
                self._session,
                commodity_id=commodity_id,
                as_of_date=as_of_date,
                market_ids=markets,
            )
        if quality_snapshot is None:
            quality_snapshot = self._quality_repo.get_by_commodity_date(
                commodity_id, as_of_date, registry_id=registry.registry_id
            )

        futures_feed_ok = _resolve_futures_feed_ok(quality_snapshot)
        near_quintal: Decimal | None = None
        far_quintal: Decimal | None = None
        oi_series: list[int] = []

        if observation_series.near_far is not None:
            near_quintal = observation_series.near_far.near.settle_price_quintal
            far_quintal = observation_series.near_far.far.settle_price_quintal

        if observation_series.oi_by_date:
            ordered_days = sorted(observation_series.oi_by_date)
            oi_series = [observation_series.oi_by_date[day] for day in ordered_days]

        features = compute_futures_features(
            near_settle_quintal=near_quintal,
            far_settle_quintal=far_quintal,
            spot_modal_quintal=spot_modal_quintal,
            oi_series=oi_series,
            futures_feed_ok=futures_feed_ok,
            confidence_base=CONFIDENCE_BASE,
            confidence_cap=CONFIDENCE_CAP_PROTOTYPE,
            thin_oi_threshold=THIN_OI_CONTRACTS,
            thin_oi_penalty_rate=THIN_OI_PENALTY,
        )

        components = features.as_components()
        components["environment"] = ENVIRONMENT_PROTOTYPE
        components["futures_feed_ok"] = FUTURES_FEED_OK_PROTOTYPE
        components["source"] = source

        source_refs = _collect_source_refs(observation_series)
        as_of_timestamp = _resolve_as_of_timestamp(observation_series, as_of_date)
        value = signed_value(
            direction=features.direction.value,
            magnitude=features.magnitude,
        )

        signal = StructuredSignal(
            agent_type=AgentType.FUTURES,
            commodity_id=CommodityType.COTTON,
            value=value,
            direction=features.direction,
            magnitude=features.magnitude,
            confidence=features.confidence,
            as_of_timestamp=as_of_timestamp,
            signal_components=components,
            source_refs=[UUID(ref) for ref in source_refs],
        )

        return FuturesSignalBundle(
            features=features,
            signal=signal,
            source_refs=tuple(UUID(ref) for ref in source_refs),
            environment=ENVIRONMENT_PROTOTYPE,
            futures_feed_ok=FUTURES_FEED_OK_PROTOTYPE,
        )

    def generate_and_persist(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        as_of_date: date,
        trace_id: UUID | None = None,
        primary_market_ids: tuple[str, ...] | None = None,
        observation_series: FuturesObservationSeries | None = None,
        spot_modal_quintal: Decimal | None = None,
        futures_observations: list[FuturesObservationModel] | None = None,
    ) -> FuturesSignalPersistResult:
        """Generate futures signal, persist StructuredSignal + SignalSnapshot."""
        registry = self._registry.get_active_config(commodity_id)
        quality = self._quality_repo.get_by_commodity_date(
            commodity_id, as_of_date, registry_id=registry.registry_id
        )

        bundle = self.generate(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            primary_market_ids=primary_market_ids,
            observation_series=observation_series,
            spot_modal_quintal=spot_modal_quintal,
            quality_snapshot=quality,
            futures_observations=futures_observations,
        )

        signal_row = StructuredSignalModel(
            signal_id=uuid4(),
            agent_type=AgentType.FUTURES.value,
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            as_of_timestamp=bundle.signal.as_of_timestamp,
            value=bundle.signal.value,
            direction=bundle.signal.direction.value,
            magnitude=bundle.signal.magnitude,
            confidence=bundle.signal.confidence,
            signal_components=bundle.signal.signal_components,
            source_observation_refs=[str(ref) for ref in bundle.source_refs],
            registry_id=registry.registry_id,
            agent_version=AGENT_VERSION,
            trace_id=trace_id,
        )
        self._signal_repo.insert_signal(signal_row)

        payload: dict[str, object] = {
            "agent_type": AgentType.FUTURES.value,
            "value": bundle.signal.value,
            "direction": bundle.signal.direction.value,
            "magnitude": bundle.signal.magnitude,
            "confidence": bundle.signal.confidence,
            "signal_components": bundle.signal.signal_components,
            "as_of_date": as_of_date,
        }

        snapshot = SignalSnapshotModel(
            snapshot_id=uuid4(),
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry.registry_id,
            signal_ids=[str(signal_row.signal_id)],
            snapshot_hash="",
            trace_id=trace_id,
            data_quality_snapshot_id=(
                quality.quality_snapshot_id if quality is not None else None
            ),
        )
        self._snapshot_repo.insert_snapshot(
            snapshot,
            signal_payloads=[payload],
        )

        return FuturesSignalPersistResult(
            bundle=bundle,
            structured_signal=signal_row,
            snapshot=snapshot,
        )


def _resolve_futures_feed_ok(
    quality_snapshot: DataQualitySnapshotModel | None,
) -> bool:
    """Prototype path always reports degraded feed (G-02)."""
    if quality_snapshot is None:
        return False
    return bool(quality_snapshot.futures_feed_ok)


def _collect_source_refs(series: FuturesObservationSeries) -> tuple[str, ...]:
    return series.source_observation_refs


def _resolve_as_of_timestamp(
    series: FuturesObservationSeries,
    as_of_date: date,
) -> datetime:
    if series.near_far is not None:
        return series.near_far.near.observed_at
    return datetime(
        as_of_date.year,
        as_of_date.month,
        as_of_date.day,
        17,
        30,
        tzinfo=UTC,
    )


def _series_from_injected(
    rows: list[FuturesObservationModel],
    *,
    as_of_date: date,
) -> FuturesObservationSeries:
    """Build series from injected observations (unit tests / replay)."""
    from backend.app.services.signals.futures.observations import (
        select_near_far_contracts,
    )

    usable = [
        row
        for row in rows
        if row.validation_status
        in {
            "validated",
            "published",
        }
    ]
    near_far = select_near_far_contracts(usable, as_of_date=as_of_date)
    oi_by_date: dict[date, int] = {}
    refs: list[str] = []
    if near_far is not None:
        near_expiry = near_far.near.expiry_date
        for row in usable:
            if row.expiry_date != near_expiry:
                continue
            refs.append(str(row.observation_id))
            if row.open_interest is not None:
                oi_by_date[row.as_of_date] = row.open_interest

    return FuturesObservationSeries(
        as_of_date=as_of_date,
        near_far=near_far,
        oi_by_date=oi_by_date,
        source_observation_refs=tuple(sorted(set(refs))),
    )
