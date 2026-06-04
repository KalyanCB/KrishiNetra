"""E-01-S11: Data foundation integration gate (FK graph, cutoff, replay inputs)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from tests.fixtures.data_foundation import (
    COTTON_TEST_AS_OF,
    COTTON_TEST_FORMULA_VERSION,
    COTTON_TEST_ID,
    COTTON_TEST_MARKET_ID,
    cleanup_cotton_test,
    seed_full_fk_graph,
)

from backend.app.persistence.replay import (
    list_price_observations_at_cutoff,
)
from backend.app.persistence.repositories.decision import DecisionSessionRepository
from backend.app.persistence.repositories.forecast import ForecastVersionRepository
from backend.app.persistence.repositories.signal import SignalSnapshotRepository
from shared.domain.enums import AgentType

pytestmark = pytest.mark.integration


def test_full_fk_graph_fixture(migrated_database: str) -> None:
    """AC-1: ``cotton_test`` fixture spans registry → observations → 6 signals → snapshot → forecast → decision."""
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        cleanup_cotton_test(session)
        graph = seed_full_fk_graph(session)
        session.commit()

        assert graph.commodity_id == COTTON_TEST_ID
        assert graph.signal_count == len(AgentType)
        assert len(graph.price_observation_ids) == 2

        snapshot = SignalSnapshotRepository(session).get_snapshot(
            COTTON_TEST_ID,
            COTTON_TEST_AS_OF,
            graph.registry.registry_id,
        )
        assert snapshot is not None
        assert snapshot.snapshot_id == graph.snapshot.snapshot_id
        assert snapshot.snapshot_hash == graph.snapshot.snapshot_hash

        forecast = ForecastVersionRepository(session).get_published(
            COTTON_TEST_ID,
            COTTON_TEST_AS_OF,
            graph.registry.registry_id,
        )
        assert forecast is not None
        assert forecast.forecast_version_id == graph.forecast_version.forecast_version_id
        assert forecast.snapshot_id == graph.snapshot.snapshot_id

        loaded_session = DecisionSessionRepository(session).get_session(
            graph.decision_session.session_id
        )
        assert loaded_session is not None
        assert loaded_session.registry_id == graph.registry.registry_id
        assert loaded_session.context_id == graph.user_context.context_id
        assert loaded_session.recommendation_id == graph.recommendation.recommendation_id
        assert graph.recommendation_version.formula_version == COTTON_TEST_FORMULA_VERSION

        row = session.execute(
            text(
                "SELECT COUNT(*) FROM structured_signal "
                "WHERE commodity_id = :cid AND as_of_date = :dt"
            ),
            {"cid": COTTON_TEST_ID, "dt": COTTON_TEST_AS_OF},
        ).scalar_one()
        assert row == len(AgentType)

        cleanup_cotton_test(session)
    engine.dispose()


def test_as_of_date_cutoff(migrated_database: str) -> None:
    """AC-2: Historical read excludes observations with ``observed_at`` after end of ``as_of_date``."""
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        cleanup_cotton_test(session)
        graph = seed_full_fk_graph(session)
        session.commit()

        visible = list_price_observations_at_cutoff(
            session,
            commodity_id=COTTON_TEST_ID,
            market_id=COTTON_TEST_MARKET_ID,
            as_of=COTTON_TEST_AS_OF,
        )
        assert len(visible) == 1
        assert visible[0].observation_id == graph.price_observation_ids[0]
        assert visible[0].value == Decimal("5500.00")

        cleanup_cotton_test(session)
    engine.dispose()
