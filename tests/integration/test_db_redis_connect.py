"""E-00-S06: PostgreSQL and Redis connectivity (skip if stack not running)."""

from __future__ import annotations

import os

import pytest

pytestmark = pytest.mark.integration


def _stack_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL") and os.environ.get("REDIS_URL"))


@pytest.mark.skipif(
    not _stack_configured(),
    reason="DATABASE_URL and REDIS_URL required (docker compose + .env)",
)
def test_db_redis_connect() -> None:
    import redis
    from sqlalchemy import create_engine, text

    db_url = os.environ["DATABASE_URL"]
    redis_url = os.environ["REDIS_URL"]

    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1

    client = redis.from_url(redis_url)
    assert client.ping() is True
