"""E-01-S01: test_alembic_upgrade_head on PostgreSQL."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

pytestmark = pytest.mark.integration


def test_alembic_upgrade_head(migrated_database: str, alembic_config: Config) -> None:
    """Head revision applied; reference tables exist; bootstrap left no early tables."""
    engine = create_engine(migrated_database, pool_pre_ping=True)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert "alembic_version" in tables
    assert "commodity" in tables
    assert "commodity_profile" in tables
    assert "region" in tables
    assert "market" in tables
    assert "price_observation" not in tables

    with engine.connect() as conn:
        assert (
            conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            == "0002_reference_entities"
        )
    engine.dispose()


@pytest.mark.skipif(
    not os.environ.get("DATABASE_URL"),
    reason="DATABASE_URL required",
)
def test_alembic_downgrade_one_revision(alembic_config: Config) -> None:
    """Reversible migrations: downgrade 0002 removes reference tables."""
    command.downgrade(alembic_config, "0001_alembic_bootstrap")
    db_url = os.environ["DATABASE_URL"]
    engine = create_engine(db_url, pool_pre_ping=True)
    inspector = inspect(engine)
    assert "commodity" not in inspector.get_table_names()
    command.upgrade(alembic_config, "head")
    engine.dispose()
