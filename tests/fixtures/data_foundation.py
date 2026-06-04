"""E-01-S11: Full data-foundation FK graph fixture (``cotton_test``)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.persistence.models.decision import (
    DecisionSessionModel,
    OutcomeModel,
    OutcomeValidationStatus,
    RecommendationModel,
    RecommendationVersionModel,
    UserContextModel,
)
from backend.app.persistence.models.forecast import (
    ForecastModel,
    ForecastVersionModel,
)
from backend.app.persistence.models.observation import (
    ObservationValidationStatus,
    PriceObservationModel,
)
from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.models.reference import (
    CommodityModel,
    CommodityStatus,
    MarketModel,
    RegionModel,
    RegionType,
)
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.models.signal import (
    SignalSnapshotModel,
    StructuredSignalModel,
)
from backend.app.persistence.repositories.decision import (
    DecisionSessionRepository,
    OutcomeRepository,
    RecommendationRepository,
    RecommendationVersionRepository,
    UserContextRepository,
)
from backend.app.persistence.repositories.forecast import (
    ForecastRepository,
    ForecastVersionRepository,
)
from backend.app.persistence.repositories.observation import PriceObservationRepository
from backend.app.persistence.repositories.quality import DataQualitySnapshotRepository
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.repositories.signal import (
    SignalSnapshotRepository,
    StructuredSignalRepository,
)
from shared.domain.enums import (
    ActionType,
    AgentType,
    Direction,
    LiquidityNeed,
    PersonaType,
)

COTTON_TEST_ID = "cotton_test"
COTTON_TEST_AS_OF = date(2026, 6, 4)
COTTON_TEST_MARKET_ID = "mkt_cotton_test"
COTTON_TEST_REGION_ID = "reg_cotton_test"
COTTON_TEST_FORMULA_VERSION = "v1.0.0"


def decision_rules() -> dict:
    return {
        "msp_proximity_pct": 0.03,
        "default_partial_sell_pct": 0.50,
        "formula_version": COTTON_TEST_FORMULA_VERSION,
    }


def horizon_payload(*, confidence: Decimal = Decimal("0.80")) -> dict:
    return {
        "point": 5500.0,
        "band_low": 5200.0,
        "band_high": 5800.0,
        "direction": Direction.BULLISH.value,
        "forecast_confidence": float(confidence),
    }


@dataclass(frozen=True)
class DataFoundationGraph:
    """End-to-end FK graph seeded for S11 integration gate."""

    commodity_id: str
    registry: CommodityRegistryModel
    region_id: str
    market_id: str
    price_observation_ids: tuple[UUID, ...]
    signal_count: int
    snapshot: SignalSnapshotModel
    forecast_version: ForecastVersionModel
    user_context: UserContextModel
    decision_session: DecisionSessionModel
    recommendation: RecommendationModel
    recommendation_version: RecommendationVersionModel
    outcome: OutcomeModel


def seed_full_fk_graph(session: Session) -> DataFoundationGraph:
    """Create ``cotton_test`` graph: registry → observations → 6 signals → snapshot → forecast → decision."""
    commodity_id = COTTON_TEST_ID
    commodity = CommodityModel(
        commodity_id=commodity_id,
        name="Cotton Test Fixture",
        status=CommodityStatus.DRAFT.value,
    )
    session.add(commodity)
    session.flush()

    region = RegionModel(
        region_id=COTTON_TEST_REGION_ID,
        commodity_id=commodity_id,
        name="Cotton Test Region",
        type=RegionType.STATE.value,
    )
    session.add(region)
    session.flush()

    market = MarketModel(
        market_id=COTTON_TEST_MARKET_ID,
        region_id=COTTON_TEST_REGION_ID,
        commodity_id=commodity_id,
        market_type="mandi",
        name="Cotton Test Mandi",
    )
    session.add(market)
    session.flush()

    registry = CommodityRegistryModel(
        registry_id=uuid4(),
        commodity_id=commodity_id,
        version="1.0.0",
        effective_from=date(2026, 1, 1),
        is_active=True,
        required_agents=["Market", "Futures"],
        decision_rules=decision_rules(),
    )
    CommodityRegistryRepository(session).insert_version(registry)

    price_repo = PriceObservationRepository(session)
    within_cutoff = price_repo.insert_observation(
        PriceObservationModel(
            observation_id=uuid4(),
            market_id=COTTON_TEST_MARKET_ID,
            commodity_id=commodity_id,
            price_type="modal",
            value=Decimal("5500.00"),
            unit="quintal",
            currency="INR",
            observed_at=datetime(2026, 6, 4, 10, 0, tzinfo=UTC),
            as_of_date=COTTON_TEST_AS_OF,
            source="agmarknet",
            validation_status=ObservationValidationStatus.PUBLISHED.value,
        )
    )
    after_cutoff_same_day = price_repo.insert_observation(
        PriceObservationModel(
            observation_id=uuid4(),
            market_id=COTTON_TEST_MARKET_ID,
            commodity_id=commodity_id,
            price_type="modal",
            value=Decimal("5600.00"),
            unit="quintal",
            currency="INR",
            observed_at=datetime(2026, 6, 5, 0, 30, tzinfo=UTC),
            as_of_date=date(2026, 6, 5),
            source="agmarknet",
            validation_status=ObservationValidationStatus.PUBLISHED.value,
        )
    )

    quality = DataQualitySnapshotModel(
        quality_snapshot_id=uuid4(),
        commodity_id=commodity_id,
        as_of_date=COTTON_TEST_AS_OF,
        registry_id=registry.registry_id,
        source_health={"agmarknet": "fresh"},
        overall_quality_score=Decimal("0.90"),
        futures_feed_ok=True,
        confidence_penalty_factor=Decimal("0"),
    )
    DataQualitySnapshotRepository(session).insert_snapshot(quality)

    signal_repo = StructuredSignalRepository(session)
    observed = datetime(2026, 6, 4, 12, 0, tzinfo=UTC)
    signal_ids: list[str] = []
    for agent in AgentType:
        row = StructuredSignalModel(
            signal_id=uuid4(),
            agent_type=agent.value,
            commodity_id=commodity_id,
            as_of_date=COTTON_TEST_AS_OF,
            as_of_timestamp=observed,
            value=Decimal("0.50"),
            direction=Direction.NEUTRAL.value,
            magnitude=Decimal("0.30"),
            confidence=Decimal("0.70"),
            registry_id=registry.registry_id,
        )
        signal_repo.insert_signal(row)
        signal_ids.append(str(row.signal_id))

    snapshot_hash = "cotton_test_snapshot_hash_v1" + "0" * 24
    snapshot = SignalSnapshotModel(
        snapshot_id=uuid4(),
        commodity_id=commodity_id,
        as_of_date=COTTON_TEST_AS_OF,
        registry_id=registry.registry_id,
        signal_ids=signal_ids,
        snapshot_hash=snapshot_hash,
        data_quality_snapshot_id=quality.quality_snapshot_id,
    )
    SignalSnapshotRepository(session).insert(snapshot)

    forecast = ForecastRepository(session).insert(
        ForecastModel(forecast_id=uuid4(), commodity_id=commodity_id)
    )
    forecast_version = ForecastVersionRepository(session).insert_version(
        ForecastVersionModel(
            forecast_version_id=uuid4(),
            forecast_id=forecast.forecast_id,
            commodity_id=commodity_id,
            as_of_date=COTTON_TEST_AS_OF,
            registry_id=registry.registry_id,
            snapshot_id=snapshot.snapshot_id,
            model_version="v0.1.0",
            horizon_30=horizon_payload(),
            horizon_60=horizon_payload(),
            horizon_90=horizon_payload(),
            is_published=True,
        )
    )

    context = UserContextRepository(session).insert_context(
        UserContextModel(
            context_id=uuid4(),
            commodity_id=commodity_id,
            quantity=Decimal("100.0000"),
            storage_access=True,
            liquidity_need=LiquidityNeed.HIGH.value,
            financing_profile={"cost_of_capital_pct": 0.12},
            risk_profile={"tier": "moderate"},
            persona_type=PersonaType.FARMER.value,
            context_hash="cotton_test_ctx" + "0" * 20,
        )
    )
    session_created_at = datetime(2026, 6, 4, 14, 0, tzinfo=UTC)
    decision_session = DecisionSessionRepository(session).insert_session(
        DecisionSessionModel(
            session_id=uuid4(),
            created_at=session_created_at,
            context_id=context.context_id,
            commodity_id=commodity_id,
            as_of_date=COTTON_TEST_AS_OF,
            registry_id=registry.registry_id,
            forecast_version_id=forecast_version.forecast_version_id,
            snapshot_id=snapshot.snapshot_id,
            mi_snapshot_ref=f"mi:{commodity_id}:{COTTON_TEST_AS_OF.isoformat()}",
            explanation_id=None,
            persona_type=PersonaType.FARMER.value,
            status="delivered",
        )
    )
    recommendation = RecommendationRepository(session).insert_recommendation(
        RecommendationModel(
            recommendation_id=uuid4(),
            session_id=decision_session.session_id,
            session_created_at=session_created_at,
            commodity_id=commodity_id,
        )
    )
    DecisionSessionRepository(session).link_recommendation(
        decision_session,
        recommendation.recommendation_id,
    )
    recommendation_version = RecommendationVersionRepository(session).insert_version(
        RecommendationVersionModel(
            recommendation_version_id=uuid4(),
            recommendation_id=recommendation.recommendation_id,
            version=1,
            action_type=ActionType.PARTIAL_SELL.value,
            net_value_after_carry=Decimal("12500.0000"),
            partial_quantity_pct=Decimal("0.5000"),
            recommendation_confidence=Decimal("0.5800"),
            net_hold_value_components={"expected_gain": 15000.0},
            rules_applied=["PARTIAL_DEFAULT_50_v1"],
            msp_proximity_triggered=False,
            formula_version=COTTON_TEST_FORMULA_VERSION,
            decision_trace={"trace": "s11_fixture"},
            is_delivered=True,
        )
    )
    outcome = OutcomeRepository(session).insert_outcome(
        OutcomeModel(
            outcome_id=uuid4(),
            session_id=decision_session.session_id,
            session_created_at=session_created_at,
            validation_status=OutcomeValidationStatus.PENDING.value,
        )
    )

    return DataFoundationGraph(
        commodity_id=commodity_id,
        registry=registry,
        region_id=COTTON_TEST_REGION_ID,
        market_id=COTTON_TEST_MARKET_ID,
        price_observation_ids=(
            within_cutoff.observation_id,
            after_cutoff_same_day.observation_id,
        ),
        signal_count=len(signal_ids),
        snapshot=snapshot,
        forecast_version=forecast_version,
        user_context=context,
        decision_session=decision_session,
        recommendation=recommendation,
        recommendation_version=recommendation_version,
        outcome=outcome,
    )


def cleanup_cotton_test(session: Session) -> None:
    """Remove ``cotton_test`` fixture rows (idempotent for reruns)."""
    commodity_id = COTTON_TEST_ID
    session.execute(
        text("DELETE FROM commodity_profile WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM outcome WHERE session_id IN "
             "(SELECT session_id FROM decision_session WHERE commodity_id = :cid)"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM recommendation_version WHERE recommendation_id IN "
             "(SELECT recommendation_id FROM recommendation WHERE commodity_id = :cid)"),
        {"cid": commodity_id},
    )
    session.execute(
        text(
            "UPDATE decision_session SET recommendation_id = NULL "
            "WHERE commodity_id = :cid"
        ),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM recommendation WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM decision_session WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM user_context WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM forecast_version WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM forecast WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM signal_snapshot WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM structured_signal WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM data_quality_snapshot WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM price_observation WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM arrival_observation WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM weather_observation WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM commodity_registry WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM market WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM region WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    commodity = session.get(CommodityModel, commodity_id)
    if commodity is not None:
        session.delete(commodity)
    session.commit()
