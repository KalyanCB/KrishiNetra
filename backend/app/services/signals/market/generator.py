"""MarketSignalGenerator — E-04-S01 deterministic market signal runtime."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from statistics import median
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    PriceObservationModel,
)
from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.models.signal import (
    SignalSnapshotModel,
    StructuredSignalModel,
)
from backend.app.persistence.repositories.observation import (
    ArrivalObservationRepository,
    PriceObservationRepository,
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
from backend.app.services.quality.metrics import VALID_VALIDATION_STATUSES
from backend.app.services.registry.service import RegistryService
from backend.app.services.signals.market.constants import (
    AGENT_VERSION,
    CONFIDENCE_BASE,
    LAG_HOURS_CAP,
    MAX_LAG_PENALTY,
    MSP_STUB_CONFIDENCE_PENALTY,
    ROLLING_WINDOW_DAYS,
    STUB_MSP_INR_QUINTAL,
    MarketSignalType,
)
from backend.app.services.signals.market.features import (
    FeatureSignal,
    composite_confidence,
    composite_direction,
    composite_magnitude,
    compute_arrival_momentum,
    compute_price_acceleration,
    compute_price_momentum,
    compute_price_vs_msp_distance,
    signed_value,
)
from shared.domain.enums import AgentType, CommodityType
from shared.signal_contract.models import StructuredSignal

MODAL_PRICE_TYPE = "modal"
MSP_RULE_KEY = "msp_inr_quintal"
MSP_PROXIMITY_KEY = "msp_proximity_pct"


@dataclass(frozen=True, slots=True)
class MarketSignalBundle:
    """Four feature signals plus composite StructuredSignal contract."""

    features: tuple[FeatureSignal, FeatureSignal, FeatureSignal, FeatureSignal]
    signal: StructuredSignal
    source_refs: tuple[UUID, ...]
    primary_markets_reporting_pct: Decimal
    msp_inr_quintal: Decimal
    msp_is_stub: bool


@dataclass(frozen=True, slots=True)
class MarketSignalPersistResult:
    """Outcome of generate_and_persist."""

    bundle: MarketSignalBundle
    structured_signal: StructuredSignalModel
    snapshot: SignalSnapshotModel


class MarketSignalGenerator:
    """
    Deterministic Market agent runtime (SIGNAL_ENGINE_V1 §3).

    Loads VALIDATED/PUBLISHED Agmarknet observations only, computes four
    feature signals, composes one StructuredSignal, and persists via Track C repos.
    """

    EMITTED_SIGNAL_TYPES: tuple[MarketSignalType, ...] = (
        MarketSignalType.PRICE_MOMENTUM,
        MarketSignalType.ARRIVAL_MOMENTUM,
        MarketSignalType.PRICE_VS_MSP_DISTANCE,
        MarketSignalType.PRICE_ACCELERATION,
    )

    def __init__(self, session: Session) -> None:
        self._session = session
        self._price_repo = PriceObservationRepository(session)
        self._arrival_repo = ArrivalObservationRepository(session)
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
        price_observations: list[PriceObservationModel] | None = None,
        arrival_observations: list[ArrivalObservationModel] | None = None,
        quality_snapshot: DataQualitySnapshotModel | None = None,
    ) -> MarketSignalBundle:
        """Compute four feature signals and composite StructuredSignal."""
        registry = self._registry.get_active_config(commodity_id)
        markets = primary_market_ids or load_telangana_primary_market_ids()
        window_start = as_of_date - timedelta(days=ROLLING_WINDOW_DAYS - 1)

        if price_observations is None:
            price_observations = self._load_validated_prices(
                commodity_id, window_start, as_of_date
            )
        if arrival_observations is None:
            arrival_observations = self._load_validated_arrivals(
                commodity_id, window_start, as_of_date
            )
        if quality_snapshot is None:
            quality_snapshot = self._quality_repo.get_by_commodity_date(
                commodity_id, as_of_date, registry_id=registry.registry_id
            )

        validated_prices = _filter_price_observations(price_observations, markets)
        validated_arrivals = _filter_arrival_observations(arrival_observations, markets)

        basket_modals = self._basket_modals_by_date(validated_prices, markets)
        basket_arrivals = self._basket_arrivals_by_date(validated_arrivals, markets)

        msp_inr, msp_is_stub = self._resolve_msp(registry.decision_rules)
        proximity = Decimal(
            str(registry.decision_rules.get(MSP_PROXIMITY_KEY, 0.03))
        )

        price_momentum = compute_price_momentum(
            basket_modals=basket_modals,
            as_of_date=as_of_date,
        )
        arrival_momentum = compute_arrival_momentum(
            basket_arrivals=basket_arrivals,
            as_of_date=as_of_date,
        )
        msp_distance = compute_price_vs_msp_distance(
            spot_modal=basket_modals.get(as_of_date),
            msp_inr_quintal=msp_inr,
            msp_proximity_pct=proximity,
            msp_is_stub=msp_is_stub,
        )
        price_acceleration = compute_price_acceleration(
            basket_modals=basket_modals,
            as_of_date=as_of_date,
        )

        features = (
            price_momentum,
            arrival_momentum,
            msp_distance,
            price_acceleration,
        )

        reporting_pct = self._primary_markets_reporting_pct(
            validated_prices, markets, as_of_date
        )
        lag_penalty = self._lag_penalty(quality_snapshot)
        msp_penalty = Decimal(str(MSP_STUB_CONFIDENCE_PENALTY)) if msp_is_stub else Decimal("0")

        direction = composite_direction(features)
        magnitude = composite_magnitude(features)
        confidence = composite_confidence(
            features=features,
            coverage_ratio=reporting_pct,
            lag_penalty=lag_penalty,
            msp_stub_penalty=msp_penalty,
            confidence_base=Decimal(str(CONFIDENCE_BASE)),
        )
        value = signed_value(direction, magnitude)

        components: dict[str, object] = {
            feature.signal_type.value: feature.to_component()
            for feature in features
        }
        components["primary_markets_reporting_pct"] = float(reporting_pct)
        components["msp_inr_quintal"] = float(msp_inr)
        components["msp_is_stub"] = msp_is_stub
        components["msp_proximity_pct"] = float(proximity)

        source_refs = self._collect_source_refs(validated_prices, validated_arrivals)
        as_of_timestamp = self._resolve_as_of_timestamp(
            validated_prices, validated_arrivals, as_of_date
        )

        signal = StructuredSignal(
            agent_type=AgentType.MARKET,
            commodity_id=CommodityType.COTTON,
            value=value,
            direction=direction,
            magnitude=magnitude,
            confidence=confidence,
            as_of_timestamp=as_of_timestamp,
            signal_components=components,
            source_refs=list(source_refs),
        )

        return MarketSignalBundle(
            features=features,
            signal=signal,
            source_refs=source_refs,
            primary_markets_reporting_pct=reporting_pct,
            msp_inr_quintal=msp_inr,
            msp_is_stub=msp_is_stub,
        )

    def generate_and_persist(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        as_of_date: date,
        trace_id: UUID | None = None,
        primary_market_ids: tuple[str, ...] | None = None,
        price_observations: list[PriceObservationModel] | None = None,
        arrival_observations: list[ArrivalObservationModel] | None = None,
    ) -> MarketSignalPersistResult:
        """Generate market signal, persist StructuredSignal + SignalSnapshot."""
        registry = self._registry.get_active_config(commodity_id)
        quality = self._quality_repo.get_by_commodity_date(
            commodity_id, as_of_date, registry_id=registry.registry_id
        )

        bundle = self.generate(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            primary_market_ids=primary_market_ids,
            price_observations=price_observations,
            arrival_observations=arrival_observations,
            quality_snapshot=quality,
        )

        signal_row = StructuredSignalModel(
            signal_id=uuid4(),
            agent_type=AgentType.MARKET.value,
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
            "agent_type": AgentType.MARKET.value,
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

        return MarketSignalPersistResult(
            bundle=bundle,
            structured_signal=signal_row,
            snapshot=snapshot,
        )

    def _load_validated_prices(
        self,
        commodity_id: str,
        start: date,
        end: date,
    ) -> list[PriceObservationModel]:
        rows = self._price_repo.list_by_commodity_date_range(commodity_id, start, end)
        return [
            row
            for row in rows
            if row.validation_status in VALID_VALIDATION_STATUSES
        ]

    def _load_validated_arrivals(
        self,
        commodity_id: str,
        start: date,
        end: date,
    ) -> list[ArrivalObservationModel]:
        rows = self._arrival_repo.list_by_commodity_date_range(
            commodity_id, start, end
        )
        return [
            row
            for row in rows
            if row.validation_status in VALID_VALIDATION_STATUSES
        ]

    @staticmethod
    def _basket_modals_by_date(
        prices: list[PriceObservationModel],
        market_ids: tuple[str, ...],
    ) -> dict[date, Decimal]:
        """Daily median of primary-market modal prices."""
        del market_ids  # filter applied upstream
        by_date_market: dict[tuple[date, str], list[Decimal]] = {}
        for row in prices:
            if row.price_type != MODAL_PRICE_TYPE:
                continue
            key = (row.as_of_date, row.market_id)
            by_date_market.setdefault(key, []).append(row.value)

        result: dict[date, Decimal] = {}
        by_date: dict[date, list[Decimal]] = {}
        for (obs_date, _market), values in by_date_market.items():
            market_modal = Decimal(str(median([float(v) for v in values])))
            by_date.setdefault(obs_date, []).append(market_modal)

        for obs_date, market_modals in by_date.items():
            result[obs_date] = Decimal(str(median([float(v) for v in market_modals])))
        return result

    @staticmethod
    def _basket_arrivals_by_date(
        arrivals: list[ArrivalObservationModel],
        market_ids: tuple[str, ...],
    ) -> dict[date, Decimal]:
        """Daily sum of primary-market arrival volumes."""
        del market_ids  # filter applied upstream
        totals: dict[date, Decimal] = {}
        for row in arrivals:
            totals[row.as_of_date] = totals.get(row.as_of_date, Decimal("0")) + row.volume
        return totals

    @staticmethod
    def _primary_markets_reporting_pct(
        prices: list[PriceObservationModel],
        market_ids: tuple[str, ...],
        as_of_date: date,
    ) -> Decimal:
        reporting = {
            row.market_id
            for row in prices
            if row.as_of_date == as_of_date and row.price_type == MODAL_PRICE_TYPE
        }
        if not market_ids:
            return Decimal("0")
        ratio = len(reporting & set(market_ids)) / len(market_ids)
        return Decimal(str(round(ratio, 4)))

    @staticmethod
    def _lag_penalty(
        quality_snapshot: DataQualitySnapshotModel | None,
    ) -> Decimal:
        if quality_snapshot is None:
            return Decimal("0")
        detail = (quality_snapshot.source_health or {}).get("agmarknet") or {}
        if not isinstance(detail, dict):
            return Decimal("0")
        lag_raw = detail.get("agmarknet_lag_hours")
        if lag_raw is None:
            nested = detail.get("detail")
            if isinstance(nested, dict):
                lag_raw = nested.get("agmarknet_lag_hours")
        if lag_raw is None:
            return Decimal("0")
        lag = float(lag_raw)
        penalty = min(MAX_LAG_PENALTY, lag / LAG_HOURS_CAP)
        return Decimal(str(round(penalty, 4)))

    @staticmethod
    def _resolve_msp(decision_rules: dict[str, object]) -> tuple[Decimal, bool]:
        raw = decision_rules.get(MSP_RULE_KEY)
        if raw is None:
            return Decimal(str(STUB_MSP_INR_QUINTAL)), True
        return Decimal(str(raw)), False

    @staticmethod
    def _collect_source_refs(
        prices: list[PriceObservationModel],
        arrivals: list[ArrivalObservationModel],
    ) -> tuple[UUID, ...]:
        ids: list[UUID] = [row.observation_id for row in prices]
        ids.extend(row.observation_id for row in arrivals)
        return tuple(sorted(set(ids), key=lambda uid: uid.int))

    @staticmethod
    def _resolve_as_of_timestamp(
        prices: list[PriceObservationModel],
        arrivals: list[ArrivalObservationModel],
        as_of_date: date,
    ) -> datetime:
        candidates: list[datetime] = [
            row.observed_at
            for row in prices
            if row.as_of_date == as_of_date
        ]
        candidates.extend(
            row.observed_at for row in arrivals if row.as_of_date == as_of_date
        )
        if candidates:
            return max(candidates)
        return datetime(
            as_of_date.year,
            as_of_date.month,
            as_of_date.day,
            18,
            0,
            tzinfo=UTC,
        )


def _filter_price_observations(
    rows: list[PriceObservationModel],
    market_ids: tuple[str, ...],
) -> list[PriceObservationModel]:
    allowed = set(market_ids)
    return [
        row
        for row in rows
        if row.market_id in allowed
        and row.validation_status in VALID_VALIDATION_STATUSES
    ]


def _filter_arrival_observations(
    rows: list[ArrivalObservationModel],
    market_ids: tuple[str, ...],
) -> list[ArrivalObservationModel]:
    allowed = set(market_ids)
    return [
        row
        for row in rows
        if row.market_id in allowed
        and row.validation_status in VALID_VALIDATION_STATUSES
    ]
