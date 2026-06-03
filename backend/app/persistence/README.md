# Persistence layer (E-01)

PostgreSQL canonical model per [TDS-006](../../../docs/tds/TDS-006-Data-Model.md), migrations per [ADR-002](../../../docs/adrs/ADR-002-schema-migrations-alembic.md).

## Migrations (Alembic)

Location: `backend/app/persistence/migrations/`  
Config: `alembic.ini` at repository root.

### Naming convention

| Pattern | Example |
|---------|---------|
| `{NNNN}_{slug}` | `0001_alembic_bootstrap`, `0002_reference_entities` |

- Four-digit sequence prefix, snake_case slug aligned to E-01 story.
- One forward revision per DDL tranche (see [E01_EXECUTION_PLAN.md](../../../docs/implementation/E01_EXECUTION_PLAN.md) §4).

### Commands (from repository root)

```bash
# Apply all migrations
uv run alembic upgrade head

# Roll back one revision (dev only per ADR-002)
uv run alembic downgrade -1

# Show current revision
uv run alembic current

# Generate new revision (after model change)
uv run alembic revision -m "slug" --autogenerate
```

`DATABASE_URL` is read from environment / `.env` via `backend.app.config.settings`.

## Session and Unit of Work

- Engine and `SessionLocal`: `database.py`
- FastAPI dependency: `dependencies.get_db`
- Transaction boundary: `unit_of_work.UnitOfWork`

## Repository patterns (E-01-S02)

| Pattern | Entities | Rule |
|---------|----------|------|
| Append-only | Observations (S04+) | Insert only |
| Immutable versioned | ForecastVersion, RecommendationVersion | No UPDATE on published numerics |
| Versioned config | CommodityRegistry (S10) | Activation swap, not in-place |

Contracts: `shared.persistence.contracts`.

## Seeds

Framework under `seeds/` — cotton data in **E-02** only.
