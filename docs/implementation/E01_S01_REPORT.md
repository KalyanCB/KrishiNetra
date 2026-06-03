# E-01-S01 Report — Database Migration Framework

**Story:** E-01-S01 | **Status:** Done | **Date:** 2026-06-03

## Acceptance criteria evidence

| AC | Evidence |
|----|----------|
| AC-1 | Alembic under `backend/app/persistence/migrations/` |
| AC-2 | `uv run alembic upgrade head` applies on empty local DB (integration test) |
| AC-3 | `database.py`: `Base`, engine, `SessionLocal`, `get_session` |
| AC-4 | Naming convention in `backend/app/persistence/README.md` |
| AC-5 | CI Postgres service + `alembic upgrade head` step in `.github/workflows/ci.yml` |

## Migration revisions

| Revision ID | Slug | Scope |
|-------------|------|-------|
| `0001_alembic_bootstrap` | bootstrap | No business tables |
| `0002_reference_entities` | reference | S03 DDL (applied with S03) |

## Implementation

| Artifact | Purpose |
|----------|---------|
| `alembic.ini` | Root config; `script_location` → migrations |
| `migrations/env.py` | `DATABASE_URL` from `backend.app.config.settings` |
| `migrations/versions/0001_alembic_bootstrap.py` | Empty chain head until S03 |
| `backend/app/config/settings.py` | Pydantic settings for DB URL |

## Test results

```
uv run pytest tests/unit/test_alembic_revision_chain.py -v  → 2 passed
uv run pytest tests/integration/test_alembic_migrations.py -v  → pass with DATABASE_URL
```

## ADR / TDS compliance

- ADR-002: migration path, forward-only prod policy documented
- No business tables in `0001` per E01_EXECUTION_PLAN §4

## Risks

- Developers must export `DATABASE_URL` for integration tests
- Port 5432 conflicts on macOS (E-00-S06 note)
