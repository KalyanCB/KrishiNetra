#!/usr/bin/env bash
# Verify PostgreSQL and Redis connectivity (E-00-S06).
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export DATABASE_URL="${DATABASE_URL:-postgresql://krishinetra:krishinetra@127.0.0.1:5432/krishinetra}"
export REDIS_URL="${REDIS_URL:-redis://127.0.0.1:6379/0}"

uv run python - <<'PY'
import os
import sys

def check_postgres() -> None:
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL not set", file=sys.stderr)
        sys.exit(1)
    try:
        from sqlalchemy import create_engine, text

        engine = create_engine(url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("PostgreSQL: OK")
    except Exception as exc:
        print(f"PostgreSQL: FAIL ({exc})", file=sys.stderr)
        sys.exit(1)


def check_redis() -> None:
    url = os.environ.get("REDIS_URL")
    if not url:
        print("REDIS_URL not set", file=sys.stderr)
        sys.exit(1)
    try:
        import redis

        client = redis.from_url(url)
        if not client.ping():
            raise RuntimeError("ping returned false")
        print("Redis: OK")
    except Exception as exc:
        print(f"Redis: FAIL ({exc})", file=sys.stderr)
        sys.exit(1)


check_postgres()
check_redis()
PY
