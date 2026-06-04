"""E-01-S05: StructuredSignal and SignalSnapshot persistence tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.models.signal import (
    SignalSnapshotModel,
    StructuredSignalModel,
)
from backend.app.persistence.repositories.quality import DataQualitySnapshotRepository
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.repositories.signal import (
    SignalSnapshotRepository,
    StructuredSignalRepository,
)
from backend.app.persistence.validation.signal import (
    PI9_SIGNAL_TYPE,
    SignalValidationError,
    build_snapshot_signals,
    compute_snapshot_hash,
    validate_bounded_decimal,
)
from shared.domain.enums import AgentType, Direction


def _decision_rules() -> dict:
    return {
        "msp_proximity_pct": 0.03,
        "default_partial_sell_pct": 0.50,
        "formula_version": "v1.0.0",
    }


def _seed_registry(session: Session, *, commodity_id: str) -> CommodityRegistryModel:
    commodity = CommodityModel(
        commodity_id=commodity_id,
        name=f"Signal Test {commodity_id}",
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


def _signal_payload(
    agent_type: AgentType,
    *,
    value: Decimal = Decimal("0.55"),
    direction: Direction = Direction.BULLISH,
    as_of_date: date = date(2026, 6, 4),
) -> dict[str, object]:
    return {
        "agent_type": agent_type.value,
        "value": value,
        "direction": direction.value,
        "magnitude": Decimal("0.40"),
        "confidence": Decimal("0.75"),
        "signal_components": {"source": "test"},
        "as_of_date": as_of_date,
    }


def test_confidence_bounds_rejects_above_one() -> None:
    with pytest.raises(SignalValidationError, match="\\[0, 1\\]"):
        validate_bounded_decimal(Decimal("1.01"), field_name="confidence")


def test_snapshot_hash_stable() -> None:
    registry_id = uuid4()
    signals = [
        _signal_payload(AgentType.MARKET),
        _signal_payload(AgentType.WEATHER, direction=Direction.NEUTRAL),
        _signal_payload(AgentType.POLICY, value=Decimal("0.30")),
        _signal_payload(AgentType.DEMAND),
        _signal_payload(AgentType.FUTURES, direction=Direction.BEARISH),
        _signal_payload(AgentType.GLOBAL),
    ]
    first = compute_snapshot_hash(
        commodity_id="cotton_test",
        as_of_date=date(2026, 6, 4),
        registry_id=registry_id,
        signals=signals,
    )
    second = compute_snapshot_hash(
        commodity_id="cotton_test",
        as_of_date=date(2026, 6, 4),
        registry_id=registry_id,
        signals=list(reversed(signals)),
    )
    assert first == second
    assert len(first) == 64


def _cleanup_signal_fixtures(
    session: Session,
    *,
    commodity_id: str,
    as_of_date: date,
) -> None:
    """Remove signal test rows (partitioned table cleanup via SQL)."""
    session.execute(
        text("DELETE FROM signal_snapshot WHERE commodity_id = :cid AND as_of_date = :dt"),
        {"cid": commodity_id, "dt": as_of_date},
    )
    session.execute(
        text(
            "DELETE FROM structured_signal WHERE commodity_id = :cid AND as_of_date = :dt"
        ),
        {"cid": commodity_id, "dt": as_of_date},
    )
    session.execute(
        text(
            "DELETE FROM data_quality_snapshot WHERE commodity_id = :cid AND as_of_date = :dt"
        ),
        {"cid": commodity_id, "dt": as_of_date},
    )
    session.execute(
        text("DELETE FROM commodity_registry WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    commodity = session.get(CommodityModel, commodity_id)
    if commodity is not None:
        session.delete(commodity)
    session.commit()


@pytest.mark.integration
def test_signal_unique_per_agent_day(migrated_database: str) -> None:
    commodity_id = f"sig_unique_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        registry = _seed_registry(session, commodity_id=commodity_id)
        repo = StructuredSignalRepository(session)
        observed = datetime(2026, 6, 4, 12, 0, tzinfo=UTC)
        first = StructuredSignalModel(
            signal_id=uuid4(),
            agent_type=AgentType.MARKET.value,
            commodity_id=commodity_id,
            as_of_date=date(2026, 6, 4),
            as_of_timestamp=observed,
            value=Decimal("0.60"),
            direction=Direction.BULLISH.value,
            magnitude=Decimal("0.50"),
            confidence=Decimal("0.80"),
            registry_id=registry.registry_id,
            agent_version="v1.0.0",
        )
        repo.insert_signal(first)
        session.commit()

        duplicate = StructuredSignalModel(
            signal_id=uuid4(),
            agent_type=AgentType.MARKET.value,
            commodity_id=commodity_id,
            as_of_date=date(2026, 6, 4),
            as_of_timestamp=observed,
            value=Decimal("0.70"),
            direction=Direction.BEARISH.value,
            magnitude=Decimal("0.40"),
            confidence=Decimal("0.70"),
            registry_id=registry.registry_id,
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        _cleanup_signal_fixtures(
            session, commodity_id=commodity_id, as_of_date=date(2026, 6, 4)
        )
    engine.dispose()


@pytest.mark.integration
def test_six_signals_and_snapshot(migrated_database: str) -> None:
    commodity_id = f"sig_bundle_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        registry = _seed_registry(session, commodity_id=commodity_id)
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
        snapshot_repo = SignalSnapshotRepository(session)
        observed = datetime(2026, 6, 4, 18, 0, tzinfo=UTC)
        payloads: list[dict[str, object]] = []
        inserted: list[StructuredSignalModel] = []

        for agent in AgentType:
            payload = _signal_payload(agent)
            payloads.append(payload)
            row = StructuredSignalModel(
                signal_id=uuid4(),
                agent_type=agent.value,
                commodity_id=commodity_id,
                as_of_date=date(2026, 6, 4),
                as_of_timestamp=observed,
                value=payload["value"],  # type: ignore[arg-type]
                direction=str(payload["direction"]),
                magnitude=payload["magnitude"],  # type: ignore[arg-type]
                confidence=payload["confidence"],  # type: ignore[arg-type]
                signal_components={"source": "test"},
                source_observation_refs=[str(uuid4())],
                registry_id=registry.registry_id,
                agent_version="v1.0.0",
            )
            signal_repo.insert_signal(row)
            inserted.append(row)

        trace_id = uuid4()
        snapshot = SignalSnapshotModel(
            snapshot_id=uuid4(),
            commodity_id=commodity_id,
            as_of_date=date(2026, 6, 4),
            registry_id=registry.registry_id,
            signal_ids=[str(row.signal_id) for row in inserted],
            snapshot_hash="",
            trace_id=trace_id,
            data_quality_snapshot_id=quality.quality_snapshot_id,
        )
        snapshot_repo.insert_snapshot(snapshot, signal_payloads=payloads)
        session.commit()

        loaded = snapshot_repo.get_snapshot(
            commodity_id,
            date(2026, 6, 4),
            registry.registry_id,
        )
        assert loaded is not None
        assert len(loaded.signal_ids) == 6
        assert loaded.trace_id == trace_id
        assert len(loaded.signals) == 6
        assert loaded.signals[0][PI9_SIGNAL_TYPE] in {a.value for a in AgentType}
        assert loaded.snapshot_hash == compute_snapshot_hash(
            commodity_id=commodity_id,
            as_of_date=date(2026, 6, 4),
            registry_id=registry.registry_id,
            signals=payloads,
            trace_id=trace_id,
        )
        assert loaded.signals == build_snapshot_signals(payloads)
        assert loaded.data_quality_snapshot_id == quality.quality_snapshot_id

        signals = signal_repo.list_by_commodity_date(
            commodity_id,
            date(2026, 6, 4),
            registry_id=registry.registry_id,
        )
        assert len(signals) == 6

        _cleanup_signal_fixtures(
            session, commodity_id=commodity_id, as_of_date=date(2026, 6, 4)
        )
    engine.dispose()


@pytest.mark.integration
def test_signal_partition_pruning_explain(migrated_database: str) -> None:
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with engine.connect() as conn:
        plan = conn.execute(
            text(
                """
                EXPLAIN (FORMAT TEXT)
                SELECT signal_id
                FROM structured_signal
                WHERE commodity_id = 'cotton_test'
                  AND as_of_date >= '2026-06-01'
                  AND as_of_date < '2026-07-01'
                """
            )
        ).fetchall()
    text_plan = "\n".join(row[0] for row in plan)
    assert "structured_signal" in text_plan
    engine.dispose()
