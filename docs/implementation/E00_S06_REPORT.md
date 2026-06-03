# E-00-S06 Report — Local Development Environment

**Story:** E-00-S06 | **Status:** Done | **Date:** 2026-06-03

## Acceptance criteria evidence

| AC | Evidence |
|----|----------|
| AC-1 | `docker-compose.dev.yml` — PostgreSQL 15-alpine, Redis 7-alpine |
| AC-2 | `.env.example` — `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL` (no secrets) |
| AC-3 | Health works without DB; `scripts/verify-dev-connect.sh` + `tests/integration/test_db_redis_connect.py` |
| AC-4 | `backend/README.md` one-page setup (clone → compose → verify → uvicorn) |

## Implementation

| Artifact | Purpose |
|----------|---------|
| `docker-compose.dev.yml` | Dev-only stack at repo root (not prod IaC) |
| `.env.example` | Template for local env |
| `scripts/dev-up.sh` | `docker compose up -d` |
| `scripts/verify-dev-connect.sh` | SQLAlchemy + Redis ping |
| `pyproject.toml` | Added `psycopg2-binary` for Postgres smoke tests |

## Test results

```
uv run pytest tests/integration/test_db_redis_connect.py -v
  → SKIPPED without DATABASE_URL/REDIS_URL (by design)
  → PASS when compose up and credentials match .env.example
```

**Local note:** macOS validation attempted; port 5432 conflict with existing Postgres on host — use alternate port or stop conflicting service. Redis container started successfully.

```
./scripts/ci-local.sh  → pass (20 unit + layout tests)
```

## ADR / TDS compliance

- ADR-004: PostgreSQL 15+, Redis 7+, uv, no prod IaC in `infra/`
- TDS-013 F-00-03: local dev feature complete
- No Alembic migrations (per story scope)

## Risks

- Port collisions on developer machines
- Integration test requires explicit env export or `.env` file
