# E-01-S04 Completion Report — Partitioned Observations

**Date:** 2026-06-04  
**Story:** E-01-S04 — PriceObservation and ArrivalObservation (Time-Series)  
**Epic:** E-01 Data Foundation  
**Migration:** `0005_observations_partitioned`

---

## Summary

Implemented append-only `price_observation` and `arrival_observation` with monthly RANGE partitioning on `as_of_date`, `observation_validation_status` enum, ORM models, append-only repositories, and integration tests. Composite primary key `(observation_id, as_of_date)` satisfies PostgreSQL partitioned-table PK rules (TDS-006 logical PK remains `observation_id`).

---

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-1 | Tables with TDS-006 §3.6–3.7 attributes | **Done** | Migration `0005_observations_partitioned.py` |
| AC-2 | Indexes `(commodity_id, as_of_date DESC)`, `(market_id, observed_at DESC)`, `(source, as_of_date)` on price | **Done** | Parent-table indexes |
| AC-3 | Monthly RANGE + DEFAULT child | **Done** | `*_2026_06` + `*_default` |
| AC-4 | `supersedes_id` nullable | **Done** | Column on both tables; lineage enforced at repository layer (no DB self-FK — PG partition constraint) |
| AC-5 | `validation_status` enum | **Done** | `observation_validation_status` |

---

## Partition Ops Playbook

| Action | Owner | Cadence |
|--------|-------|---------|
| Add next month child (`ATTACH` / forward migration) | Ops | Before calendar month start |
| DEFAULT partition | Migration | Catches rows until child exists |
| 7-year hot retention | Ops (future) | Per TDS-006 §3.6; `OBSERVATION_RETENTION_YEARS = 7` in model module |

Initial child: **2026-06** (`2026-06-01` ≤ `as_of_date` < `2026-07-01`).

---

## Deliverables

| Artifact | Path |
|----------|------|
| Migration | `backend/app/persistence/migrations/versions/0005_observations_partitioned.py` |
| ORM | `backend/app/persistence/models/observation.py` |
| Repositories | `backend/app/persistence/repositories/observation.py` |
| Validation | `backend/app/persistence/validation/observation.py` |
| UoW wiring | `backend/app/persistence/unit_of_work.py` |
| Tests | `tests/unit/test_observations.py` |

---

## Tests

| Test | Type | Status |
|------|------|--------|
| `test_validation_status_enum_rejects_invalid` | Unit | Pass |
| `test_validation_status_enum_accepts_all_values` | Unit | Pass |
| `test_price_observation_append_only` | Integration | Requires `DATABASE_URL` |
| `test_price_observation_invalid_market_fk` | Integration | Requires `DATABASE_URL` |
| `test_partition_pruning_explain` | Integration | Requires `DATABASE_URL` |
| `test_arrival_observation_insert` | Integration | Requires `DATABASE_URL` |
| `test_alembic_revision_chain_linear` | Unit | Pass (head `0005`) |

---

## Quality Gates

| Check | Result |
|-------|--------|
| `uv run ruff check .` | See Phase 3 executive summary |
| `uv run mypy` | See Phase 3 executive summary |
| `uv run pytest tests/ -v` | See Phase 3 executive summary |
| `alembic upgrade head` | See Phase 3 executive summary |

---

## E-03 Prep (no implementation)

Observations ready for `PRICE_UPDATED` / `ARRIVAL_UPDATED` event emission (TDS-005) in E-03; no ingest code in this story.

---

*End of E-01-S04 completion report.*
