# Repository pattern (E-01-S02)

Aligned to [TDS-006 §6–§8](../../../docs/tds/TDS-006-Data-Model.md) and [ADR-002](../../../docs/adrs/ADR-002-schema-migrations-alembic.md).

## Patterns

| Pattern | Tables | Repository rule |
|---------|--------|-----------------|
| **Append-only** | `price_observation`, `arrival_observation` (S04+) | `insert` only; corrections via new row + `supersedes_id` |
| **Immutable versioned** | `forecast_version`, `recommendation_version` (S06, S07) | `insert` only; `update()` raises `ImmutableVersionUpdateError` |
| **Versioned config** | `commodity_registry` (S10) | New version row; exactly one `is_active=true` per commodity; `RegistryService.get_active_config()` |
| **Quality snapshot** | `data_quality_snapshot` (S08) | Insert with bounds validation; UNIQUE per (commodity, date, registry) |
| **Reference / mutable profile** | `commodity`, `commodity_profile`, `region`, `market` | `get_by_id`, `insert`; profile updated in place per TDS-006 §3.2 |

## Base types

- `BaseRepository` — `get_by_id`, `insert`
- `ImmutableVersionRepository` — blocks `update()` for version tables
- `UnitOfWork` — single transaction across repositories

Contracts live in `shared.persistence.contracts`.

## Usage

```python
with UnitOfWork() as uow:
    uow.commodities.insert(commodity)
    uow.commit()
```

FastAPI routes use `dependencies.get_db` for request-scoped sessions.
