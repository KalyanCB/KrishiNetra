"""E-01-S01: test_alembic_upgrade_head on PostgreSQL."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

pytestmark = pytest.mark.integration


def test_alembic_upgrade_head(migrated_database: str, alembic_config: Config) -> None:
    """Head revision applied; full E-01 Phase 4 schema present."""
    engine = create_engine(migrated_database, pool_pre_ping=True)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "alembic_version" in tables
    assert "commodity" in tables
    assert "commodity_profile" in tables
    assert "region" in tables
    assert "market" in tables
    assert "commodity_registry" in tables
    assert "data_quality_snapshot" in tables
    assert "price_observation" in tables
    assert "arrival_observation" in tables
    assert "structured_signal" in tables
    assert "signal_snapshot" in tables
    assert "forecast" in tables
    assert "forecast_version" in tables
    assert "feature_set" in tables
    assert "feature_vector" in tables
    assert "user_context" in tables
    assert "decision_session" in tables
    assert "recommendation" in tables
    assert "recommendation_version" in tables
    assert "outcome" in tables
    assert "weather_observation" in tables

    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == "0011_observation_rejected"
        )
    engine.dispose()


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL required",
)
def test_alembic_downgrade_one_revision(alembic_config: Config) -> None:
    """Reversible migrations: downgrade one step from head (0011 -> 0010)."""
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "-1")
    db_url = os.environ["DATABASE_URL"]
    engine = create_engine(db_url, pool_pre_ping=True)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "weather_observation" in tables
    assert "price_observation_2023_06" in tables
    assert "user_context" in tables
    assert "decision_session" in tables
    assert "recommendation" in tables
    assert "recommendation_version" in tables
    assert "outcome" in tables
    assert "forecast_version" in tables
    assert "forecast" in tables
    assert "structured_signal" in tables
    assert "signal_snapshot" in tables
    assert "commodity" in tables
    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == "0010_partition_backfill"
        )
    command.upgrade(alembic_config, "head")
    engine.dispose()
