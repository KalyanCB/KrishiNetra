# E-01-S05 Completion Report — StructuredSignal and SignalSnapshot

**Date:** 2026-06-04  
**Story:** E-01-S05 — StructuredSignal and SignalSnapshot  
**Epic:** E-01 Data Foundation  
**Migration:** `0006_signals_partitioned`

---

## Summary

Implemented `structured_signal` (monthly RANGE partition on `as_of_date`) and non-partitioned `signal_snapshot` per TDS-006 §3.8–3.9, §9. ORM models, insert-only repositories, bounds validation, deterministic `snapshot_hash`, and integration tests including six-signal bundle + quality snapshot FK.

---

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-1 | UNIQUE (`commodity_id`, `as_of_date`, `agent_type`, `registry_id`) on `structured_signal` | **Done** | Migration index `uq_signal_commodity_date_agent_registry` |
| AC-2 | `signal_snapshot` with `signal_ids`, `snapshot_hash`, `data_quality_snapshot_id` nullable | **Done** | Migration + `models/signal.py` |
| AC-3 | UNIQUE (`commodity_id`, `as_of_date`, `registry_id`) on snapshot | **Done** | Constraint `uq_snapshot_commodity_date_registry` |
| AC-4 | `signal_components` JSON on structured_signal | **Done** | JSONB column |
| AC-5 | Repository `get_snapshot(commodity_id, as_of_date, registry_id)` | **Done** | `SignalSnapshotRepository.get_snapshot` |

---

## Deliverables

| Artifact | Path |
|----------|------|
| Migration | `backend/app/persistence/migrations/versions/0006_signals_partitioned.py` |
| ORM | `backend/app/persistence/models/signal.py` |
| Repositories | `backend/app/persistence/repositories/signal.py` |
| Validation / hash | `backend/app/persistence/validation/signal.py` |
| UoW wiring | `backend/app/persistence/unit_of_work.py` |

---

## TDS-006 Field Alignment

| TDS-006 attribute | Column | Notes |
|-------------------|--------|-------|
| `agent_type` | `agent_type` | Values from `shared.domain.AgentType` |
| `direction` | `direction` | `shared.domain.Direction` |
| `confidence`, `magnitude` | Numeric(5,4) | Validated [0, 1] |
| `signal_components` | JSONB | Weather acreage lives here (TDS-004) |
| `source_observation_refs[]` | JSONB | Lineage to observations; no DB FK (partition-safe) |
| `agent_version` | `agent_version` | Provenance string |
| `snapshot_hash` | VARCHAR(64) | SHA-256 canonical JSON (REQ-103 prep) |

---

## Immutability

- **Insert-only** at repository layer — no UPDATE methods on signal tables (consistent with TDS-006 append-only / immutable bundle pattern).
- Corrections require new `as_of_date` or registry version, not in-place mutation.

---

## Partitioning

| Table | Strategy |
|-------|----------|
| `structured_signal` | Monthly RANGE on `as_of_date`; initial child `2026_06` + DEFAULT |
| `signal_snapshot` | **Not partitioned** (one row per commodity/day/registry; TDS-006 §9) |

Retention constant: `STRUCTURED_SIGNAL_RETENTION_YEARS = 3` (TDS-006 §3.8).

---

## Tests

| Test | Type | Status |
|------|------|--------|
| `test_confidence_bounds_rejects_above_one` | Unit | Pass |
| `test_snapshot_hash_stable` | Unit | Pass |
| `test_signal_unique_per_agent_day` | Integration | Skip without `DATABASE_URL` |
| `test_six_signals_and_snapshot` | Integration | Skip without `DATABASE_URL` |
| `test_signal_partition_pruning_explain` | Integration | Skip without `DATABASE_URL` |

---

## Quality Gates

| Check | Result |
|-------|--------|
| `uv run ruff check .` | See Phase 4 executive summary |
| `uv run mypy` | See Phase 4 executive summary |
| `uv run pytest tests/ -v` | See Phase 4 executive summary |
| `alembic upgrade head` | Head `0006_signals_partitioned` |

---

*End of E-01-S05 completion report.*
