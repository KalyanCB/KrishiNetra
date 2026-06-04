"""E-01-S07: Decision session stack persistence tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
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
from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
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
from backend.app.persistence.repositories.quality import DataQualitySnapshotRepository
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.repositories.signal import (
    SignalSnapshotRepository,
    StructuredSignalRepository,
)
from backend.app.persistence.validation.decision import (
    DecisionValidationError,
    validate_action_type,
    validate_recommendation_confidence,
)
from shared.domain.enums import (
    ActionType,
    AgentType,
    Direction,
    LiquidityNeed,
    PersonaType,
)
from shared.persistence.contracts import ImmutableVersionUpdateError


def _decision_rules() -> dict:
    return {
        "msp_proximity_pct": 0.03,
        "default_partial_sell_pct": 0.50,
        "formula_version": "v1.0.0",
    }


def _horizon_payload(*, confidence: Decimal = Decimal("0.80")) -> dict:
    return {
        "point": 5500.0,
        "band_low": 5200.0,
        "band_high": 5800.0,
        "direction": Direction.BULLISH.value,
        "forecast_confidence": float(confidence),
    }


def _seed_registry(session: Session, *, commodity_id: str) -> CommodityRegistryModel:
    commodity = CommodityModel(
        commodity_id=commodity_id,
        name=f"Decision Test {commodity_id}",
        status=CommodityStatus.DRAFT.value,
    )
    session.add(commodity)
    session.flush()
    registry = CommodityRegistryModel(
        registry_id=uuid4(),
        commodity_id=commodity_id,
        version="1.0.0",
        effective_from=date(2026, 1, 1),
        is_active=True,
        required_agents=["Market", "Futures"],
        decision_rules=_decision_rules(),
    )
    CommodityRegistryRepository(session).insert_version(registry)
    return registry


def _seed_snapshot(
    session: Session,
    *,
    commodity_id: str,
    registry: CommodityRegistryModel,
) -> SignalSnapshotModel:
    quality = DataQualitySnapshotModel(
        quality_snapshot_id=uuid4(),
        commodity_id=commodity_id,
        as_of_date=date(2026, 6, 4),
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
            as_of_date=date(2026, 6, 4),
            as_of_timestamp=observed,
            value=Decimal("0.50"),
            direction=Direction.NEUTRAL.value,
            magnitude=Decimal("0.30"),
            confidence=Decimal("0.70"),
            registry_id=registry.registry_id,
        )
        signal_repo.insert_signal(row)
        signal_ids.append(str(row.signal_id))

    snapshot = SignalSnapshotModel(
        snapshot_id=uuid4(),
        commodity_id=commodity_id,
        as_of_date=date(2026, 6, 4),
        registry_id=registry.registry_id,
        signal_ids=signal_ids,
        snapshot_hash="abc123" * 10 + "abcd",
        data_quality_snapshot_id=quality.quality_snapshot_id,
    )
    SignalSnapshotRepository(session).insert(snapshot)
    return snapshot


def _seed_forecast_version(
    session: Session,
    *,
    commodity_id: str,
    registry: CommodityRegistryModel,
    snapshot: SignalSnapshotModel,
) -> ForecastVersionModel:
    forecast = ForecastRepository(session).insert(
        ForecastModel(forecast_id=uuid4(), commodity_id=commodity_id)
    )
    return ForecastVersionRepository(session).insert_version(
        ForecastVersionModel(
            forecast_version_id=uuid4(),
            forecast_id=forecast.forecast_id,
            commodity_id=commodity_id,
            as_of_date=date(2026, 6, 4),
            registry_id=registry.registry_id,
            snapshot_id=snapshot.snapshot_id,
            model_version="v0.1.0",
            horizon_30=_horizon_payload(),
            horizon_60=_horizon_payload(),
            horizon_90=_horizon_payload(),
            is_published=True,
        )
    )


def _insert_decision_stack(
    session: Session,
    *,
    commodity_id: str,
    registry: CommodityRegistryModel,
    snapshot: SignalSnapshotModel,
    forecast_version: ForecastVersionModel,
) -> tuple[
    UserContextModel,
    DecisionSessionModel,
    RecommendationModel,
    RecommendationVersionModel,
]:
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
            context_hash="ctxhash" * 8,
        )
    )
    session_created_at = datetime(2026, 6, 4, 14, 0, tzinfo=UTC)
    decision_session = DecisionSessionRepository(session).insert_session(
        DecisionSessionModel(
            session_id=uuid4(),
            created_at=session_created_at,
            context_id=context.context_id,
            commodity_id=commodity_id,
            as_of_date=date(2026, 6, 4),
            registry_id=registry.registry_id,
            forecast_version_id=forecast_version.forecast_version_id,
            snapshot_id=snapshot.snapshot_id,
            mi_snapshot_ref=f"mi:{commodity_id}:2026-06-04",
            explanation_id=uuid4(),
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
    version = RecommendationVersionRepository(session).insert_version(
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
            formula_version="1.0.0",
            decision_trace={"trace": "schema_only"},
            is_delivered=True,
        )
    )
    return context, decision_session, recommendation, version


def _cleanup_decision_fixtures(session: Session, *, commodity_id: str) -> None:
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
        text(
            "DELETE FROM forecast_version WHERE commodity_id = :cid AND as_of_date = :dt"
        ),
        {"cid": commodity_id, "dt": date(2026, 6, 4)},
    )
    session.execute(
        text("DELETE FROM forecast WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM signal_snapshot WHERE commodity_id = :cid AND as_of_date = :dt"),
        {"cid": commodity_id, "dt": date(2026, 6, 4)},
    )
    session.execute(
        text(
            "DELETE FROM structured_signal WHERE commodity_id = :cid AND as_of_date = :dt"
        ),
        {"cid": commodity_id, "dt": date(2026, 6, 4)},
    )
    session.execute(
        text(
            "DELETE FROM data_quality_snapshot WHERE commodity_id = :cid AND as_of_date = :dt"
        ),
        {"cid": commodity_id, "dt": date(2026, 6, 4)},
    )
    session.execute(
        text("DELETE FROM commodity_registry WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    commodity = session.get(CommodityModel, commodity_id)
    if commodity is not None:
        session.delete(commodity)
    session.commit()


def test_action_type_enum_rejects_invalid_value() -> None:
    with pytest.raises(DecisionValidationError, match="action_type"):
        validate_action_type("INVALID_ACTION")


def test_recommendation_confidence_bounds_rejects_above_one() -> None:
    with pytest.raises(DecisionValidationError, match="\\[0, 1\\]"):
        validate_recommendation_confidence(Decimal("1.05"))


def test_recommendation_version_immutable() -> None:
    from unittest.mock import MagicMock

    session = MagicMock(spec=Session)
    repo = RecommendationVersionRepository(session)
    with pytest.raises(ImmutableVersionUpdateError, match="UPDATE blocked"):
        repo.update(RecommendationVersionModel())  # type: ignore[call-arg]


@pytest.mark.integration
def test_decision_session_fk_chain(migrated_database: str) -> None:
    commodity_id = f"dec_fk_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        registry = _seed_registry(session, commodity_id=commodity_id)
        snapshot = _seed_snapshot(
            session, commodity_id=commodity_id, registry=registry
        )
        forecast_version = _seed_forecast_version(
            session,
            commodity_id=commodity_id,
            registry=registry,
            snapshot=snapshot,
        )
        context, decision_session, recommendation, version = _insert_decision_stack(
            session,
            commodity_id=commodity_id,
            registry=registry,
            snapshot=snapshot,
            forecast_version=forecast_version,
        )
        session.commit()

        loaded = DecisionSessionRepository(session).get_session(
            decision_session.session_id
        )
        assert loaded is not None
        assert loaded.context_id == context.context_id
        assert loaded.forecast_version_id == forecast_version.forecast_version_id
        assert loaded.snapshot_id == snapshot.snapshot_id
        assert loaded.recommendation_id == recommendation.recommendation_id
        assert loaded.explanation_id is not None
        assert loaded.mi_snapshot_ref == f"mi:{commodity_id}:2026-06-04"

        rec = RecommendationRepository(session).get_by_session_id(
            decision_session.session_id
        )
        assert rec is not None
        assert version.recommendation_confidence == Decimal("0.5800")
        assert version.action_type == ActionType.PARTIAL_SELL.value
        assert version.recommendation_confidence != forecast_version.horizon_30[
            "forecast_confidence"
        ]

        _cleanup_decision_fixtures(session, commodity_id=commodity_id)
    engine.dispose()


@pytest.mark.integration
def test_one_outcome_per_session(migrated_database: str) -> None:
    commodity_id = f"dec_out_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        registry = _seed_registry(session, commodity_id=commodity_id)
        snapshot = _seed_snapshot(
            session, commodity_id=commodity_id, registry=registry
        )
        forecast_version = _seed_forecast_version(
            session,
            commodity_id=commodity_id,
            registry=registry,
            snapshot=snapshot,
        )
        _, decision_session, _, _ = _insert_decision_stack(
            session,
            commodity_id=commodity_id,
            registry=registry,
            snapshot=snapshot,
            forecast_version=forecast_version,
        )
        OutcomeRepository(session).insert_outcome(
            OutcomeModel(
                outcome_id=uuid4(),
                session_id=decision_session.session_id,
                session_created_at=decision_session.created_at,
                validation_status=OutcomeValidationStatus.PENDING.value,
            )
        )
        session.commit()

        duplicate = OutcomeModel(
            outcome_id=uuid4(),
            session_id=decision_session.session_id,
            session_created_at=decision_session.created_at,
            validation_status=OutcomeValidationStatus.PENDING.value,
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        _cleanup_decision_fixtures(session, commodity_id=commodity_id)
    engine.dispose()
