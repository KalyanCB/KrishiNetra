"""Shared pytest fixtures for persistence integration tests."""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text


def database_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    """Alembic config pointing at repo-root alembic.ini."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    return Config(str(root / "alembic.ini"))


@pytest.fixture(scope="session")
def migrated_database(alembic_config: Config) -> str:
    """
    Run alembic upgrade head once per session when DATABASE_URL is set.
    Yields the database URL for integration tests.
    """
    if not database_configured():
        pytest.skip("DATABASE_URL required for persistence integration tests")

    db_url = os.environ["DATABASE_URL"]
    alembic_config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_config, "head")

    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        version = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        assert version == "0011_observation_rejected"

    engine.dispose()
    return db_url


@pytest.fixture(autouse=True)
def _ensure_db_at_migration_head(
    request: pytest.FixtureRequest,
    alembic_config: Config,
) -> None:
    """
    Re-apply head before each integration test.

    Tests such as test_alembic_downgrade_one_revision temporarily downgrade;
    without this, later tests see a stale schema while migrated_database is cached.
    """
    if not database_configured():
        return
    if request.node.get_closest_marker("integration") is None:
        return
    if request.node.name == "test_alembic_downgrade_one_revision":
        return
    db_url = os.environ["DATABASE_URL"]
    alembic_config.set_main_option("sqlalchemy.url", db_url)
    command.upgrade(alembic_config, "head")
