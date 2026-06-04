"""PI10 Track C: ForecastFeatureSnapshot persistence and assembly tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.app.persistence.models.forecast import (
    FeatureVectorModel,
    ForecastFeatureSnapshotModel,
)
from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.models.signal import StructuredSignalModel
from backend.app.persistence.repositories.forecast import (
    ForecastFeatureSnapshotRepository,
)
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.validation.forecast_features import (
    ForecastFeatureValidationError,
    compute_feature_hash,
    validate_trace_id,
)
from backend.app.services.forecast.features.assembler import assemble_forecast_features
from backend.app.services.forecast.features.futures_stub import (
    FUTURES_STUB_REASON,
    build_futures_signal_stub,
)
from backend.app.services.forecast.features.service import ForecastFeatureStoreService
from shared.domain.enums import AgentType, Direction
from shared.persistence.contracts import ImmutableVersionUpdateError


def _decision_rules() -> dict:
    return {
        "msp_proximity_pct": 0.03,
        "default_partial_sell_pct": 0.50,
        "formula_version": "v1.0.0",
    }


def _seed_registry(session: Session, *, commodity_id: str) -> CommodityRegistryModel:
    commodity = CommodityModel(
        commodity_id=commodity_id,
        name=f"Feature Store Test {commodity_id}",
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


def _market_signal(
    *,
    commodity_id: str,
    registry_id: UUID,
    as_of_date: date,
    trace_id: UUID | None = None,
) -> StructuredSignalModel:
    return StructuredSignalModel(
        signal_id=uuid4(),
        agent_type=AgentType.MARKET.value,
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        as_of_timestamp=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        value=Decimal("0.42"),
        direction=Direction.BULLISH.value,
        magnitude=Decimal("0.55"),
        confidence=Decimal("0.72"),
        signal_components={
            "price_momentum": {
                "raw_value": 1.2,
                "direction": Direction.BULLISH.value,
                "magnitude": 0.4,
            },
            "arrival_momentum": 0.1,
        },
        registry_id=registry_id,
        agent_version="market-v1.0.0",
        trace_id=trace_id,
    )


def _weather_signal(
    *,
    commodity_id: str,
    registry_id: UUID,
    as_of_date: date,
    trace_id: UUID | None = None,
) -> StructuredSignalModel:
    return StructuredSignalModel(
        signal_id=uuid4(),
        agent_type=AgentType.WEATHER.value,
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        as_of_timestamp=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        value=Decimal("-0.20"),
        direction=Direction.BEARISH.value,
        magnitude=Decimal("0.35"),
        confidence=Decimal("0.81"),
        signal_components={
            "rainfall_deviation": -0.15,
            "primary_driver": "rainfall_deviation",
        },
        registry_id=registry_id,
        agent_version="weather-v1.0.0",
        trace_id=trace_id,
    )


def test_validate_trace_id_required() -> None:
    with pytest.raises(ForecastFeatureValidationError, match="trace_id"):
        validate_trace_id(None)


def test_compute_feature_hash_stable() -> None:
    registry_id = uuid4()
    trace_id = uuid4()
    values = {"market.direction": "bullish", "weather.magnitude": 0.35}
    first = compute_feature_hash(
        commodity_id="cotton",
        as_of_date=date(2026, 6, 4),
        registry_id=registry_id,
        feature_values=values,
        trace_id=trace_id,
    )
    second = compute_feature_hash(
        commodity_id="cotton",
        as_of_date=date(2026, 6, 4),
        registry_id=registry_id,
        feature_values={"weather.magnitude": 0.35, "market.direction": "bullish"},
        trace_id=trace_id,
    )
    assert first == second
    assert len(first) == 64


def test_assemble_real_futures_signal_not_stub() -> None:
    """Explicit Futures StructuredSignal maps without futures.stub flag."""
    as_of = date(2026, 6, 4)
    market = _market_signal(
        commodity_id="cotton",
        registry_id=uuid4(),
        as_of_date=as_of,
    )
    weather = _weather_signal(
        commodity_id="cotton",
        registry_id=uuid4(),
        as_of_date=as_of,
    )
    futures_model = StructuredSignalModel(
        signal_id=uuid4(),
        agent_type=AgentType.FUTURES.value,
        commodity_id="cotton",
        as_of_date=as_of,
        as_of_timestamp=datetime(2026, 6, 4, 12, 0, tzinfo=UTC),
        value=Decimal("0.10"),
        direction=Direction.BULLISH.value,
        magnitude=Decimal("0.20"),
        confidence=Decimal("0.30"),
        signal_components={"curve_slope": 0.05, "futures_feed_ok": False},
        registry_id=uuid4(),
        agent_version="futures-v1.0.0-prototype",
    )
    values, lineage = assemble_forecast_features(
        as_of_date=as_of,
        market=market,
        weather=weather,
        futures=futures_model,
        use_futures_stub=False,
    )
    assert values["futures.components.curve_slope"] == 0.05
    assert "futures.stub" not in values
    futures_lineage = lineage["agents"][AgentType.FUTURES.value]
    assert isinstance(futures_lineage, dict)
    assert futures_lineage["source"] == "structured_signal"


def test_assemble_includes_futures_stub_by_default() -> None:
    as_of = date(2026, 6, 4)
    market = _market_signal(
        commodity_id="cotton",
        registry_id=uuid4(),
        as_of_date=as_of,
    )
    weather = _weather_signal(
        commodity_id="cotton",
        registry_id=uuid4(),
        as_of_date=as_of,
    )
    values, lineage = assemble_forecast_features(
        as_of_date=as_of,
        market=market,
        weather=weather,
    )
    assert values["market.direction"] == Direction.BULLISH.value
    assert values["weather.magnitude"] == 0.35
    assert values["futures.stub"] is True
    assert values["futures.components.curve_slope"] == 0.0
    agents = lineage["agents"]
    assert isinstance(agents, dict)
    futures_lineage = agents[AgentType.FUTURES.value]
    assert isinstance(futures_lineage, dict)
    assert futures_lineage["source"] == "stub"
    assert futures_lineage["stub_reason"] == FUTURES_STUB_REASON


def test_futures_stub_is_deterministic() -> None:
    as_of = date(2026, 6, 4)
    first = build_futures_signal_stub(as_of_date=as_of)
    second = build_futures_signal_stub(as_of_date=as_of)
    assert first.signal_components == second.signal_components
    assert first.direction == second.direction


def test_forecast_feature_snapshot_repository_update_blocked() -> None:
    session = MagicMock(spec=Session)
    repo = ForecastFeatureSnapshotRepository(session)
    with pytest.raises(ImmutableVersionUpdateError, match="UPDATE blocked"):
        repo.update(ForecastFeatureSnapshotModel())  # type: ignore[call-arg]


def test_insert_snapshot_sets_hash_and_trace_id() -> None:
    session = MagicMock(spec=Session)
    repo = ForecastFeatureSnapshotRepository(session)
    entity = ForecastFeatureSnapshotModel(
        feature_set_id=uuid4(),
        commodity_id="cotton",
        as_of_date=date(2026, 6, 4),
        registry_id=uuid4(),
        feature_hash="",
    )
    values: dict[str, object] = {"market.value": 0.42}
    lineage: dict[str, object] = {
        "assembly_version": "forecast-features-v1.0.0",
        "agents": {},
    }

    original_insert = repo.insert

    def _fake_insert(model: ForecastFeatureSnapshotModel) -> ForecastFeatureSnapshotModel:
        return model

    repo.insert = _fake_insert  # type: ignore[method-assign, assignment]
    try:
        result = repo.insert_snapshot(
            entity,
            feature_values=values,
            feature_lineage=lineage,
            persist_vectors=False,
        )
    finally:
        repo.insert = original_insert  # type: ignore[method-assign]
    assert result.trace_id is not None
    assert len(result.feature_hash) == 64
    assert result.feature_values == values
    assert result.feature_lineage == lineage


def _cleanup_feature_fixtures(
    session: Session,
    *,
    commodity_id: str,
) -> None:
    session.execute(
        text(
            "DELETE FROM feature_vector WHERE feature_set_id IN "
            "(SELECT feature_set_id FROM feature_set WHERE commodity_id = :cid)"
        ),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM feature_set WHERE commodity_id = :cid"),
        {"cid": commodity_id},
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
def test_forecast_feature_store_persists_snapshot(migrated_database: str) -> None:
    commodity_id = f"ffs_{uuid4().hex[:8]}"
    as_of = date(2026, 6, 4)
    trace_id = uuid4()
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        registry = _seed_registry(session, commodity_id=commodity_id)
        market = _market_signal(
            commodity_id=commodity_id,
            registry_id=registry.registry_id,
            as_of_date=as_of,
            trace_id=trace_id,
        )
        weather = _weather_signal(
            commodity_id=commodity_id,
            registry_id=registry.registry_id,
            as_of_date=as_of,
            trace_id=trace_id,
        )

        service = ForecastFeatureStoreService(session)
        result = service.persist_from_signals(
            commodity_id=commodity_id,
            as_of_date=as_of,
            registry_id=registry.registry_id,
            market=market,
            weather=weather,
            trace_id=trace_id,
            snapshot_trace_id=trace_id,
        )
        session.commit()

        loaded = service.get_snapshot(commodity_id, as_of, registry.registry_id)
        assert loaded is not None
        assert loaded.trace_id == trace_id
        assert "futures.direction" in loaded.feature_values
        loaded_agents = loaded.feature_lineage["agents"]
        assert isinstance(loaded_agents, dict)
        futures_lineage = loaded_agents[AgentType.FUTURES.value]
        assert isinstance(futures_lineage, dict)
        market_lineage = loaded_agents[AgentType.MARKET.value]
        assert isinstance(market_lineage, dict)
        assert market_lineage["signal_id"] == str(market.signal_id)
        assert loaded.feature_hash == result.snapshot.feature_hash

        by_trace = service.get_snapshot_by_trace_id(trace_id)
        assert by_trace is not None
        assert by_trace.feature_set_id == loaded.feature_set_id

        vectors = session.scalars(
            select(FeatureVectorModel).where(
                FeatureVectorModel.feature_set_id == loaded.feature_set_id
            )
        ).all()
        assert len(vectors) == len(loaded.feature_values)

        _cleanup_feature_fixtures(session, commodity_id=commodity_id)
    engine.dispose()
