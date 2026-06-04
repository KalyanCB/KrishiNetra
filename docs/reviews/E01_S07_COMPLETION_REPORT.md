# E-01-S07 Completion Report — Decision Session Stack

**Date:** 2026-06-04  
**Story:** E-01-S07 — Decision Session Stack (UserContext through Outcome)  
**Epic:** E-01 Data Foundation  
**Migration:** `0008_decision_stack`  
**S07 status:** **Complete**

---

## Summary

Implemented decision flywheel persistence per TDS-006 §3.12–3.16: `user_context`, quarterly-partitioned `decision_session`, `recommendation`, immutable `recommendation_version`, and `outcome`. ORM models, insert-only repositories (`RecommendationVersionRepository` extends `ImmutableVersionRepository`), field validation (`recommendation_confidence` ∈ [0,1], `action_type` / persona / liquidity enums), and integration tests for full FK chain and one-outcome-per-session constraint.

**No decision engine, recommendation logic, or explanation generation** — schema and persistence only. `explanation_id` on `decision_session` is a nullable UUID ref (TDS-006 DM2-003); no explanation table in E-01.

---

## Quality Gates (2026-06-04)

| Gate | Result | Notes |
|------|--------|-------|
| `uv run alembic heads` | **Pass** | Single head: `0008_decision_stack` |
| `uv run alembic upgrade head` | **Pass** | `DATABASE_URL` → `127.0.0.1:5433` |
| `uv run ruff check` (S07 scope) | **Pass** | `backend/app/persistence/`, S07 tests, alembic chain tests |
| `uv run mypy backend/app/persistence/` | **Pass** | 42 source files |
| `uv run pytest tests/unit/test_decisions.py` | **5 passed** | All S07 tests |
| `uv run pytest tests/` (no `DATABASE_URL`) | **52 passed**, 23 skipped | Excludes S11 gate WIP (`test_data_foundation_gate.py`) |
| `uv run pytest tests/` (`DATABASE_URL` @5433, `REDIS_URL`) | **75 passed** | Excludes S11 gate WIP; `kn-test-pg` @ `127.0.0.1:5433` |

**S07 test count:** **5** (`tests/unit/test_decisions.py`)

---

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-1 | Tables: `user_context`, `decision_session`, `recommendation`, `recommendation_version`, `outcome` | **Done** | Migration `0008_decision_stack.py` |
| AC-2 | `user_context`: persona_type farmer/trader; financing_profile JSON; liquidity_need enum | **Done** | PG enums + ORM; `validate_user_context_fields` |
| AC-3 | `recommendation_version`: action_type enum; `recommendation_confidence`; `partial_quantity_pct`; `decision_trace` JSONB; `rules_applied` | **Done** | Columns + `validate_recommendation_version_fields` |
| AC-4 | `decision_session` links context, forecast_version, snapshot, registry, mi_snapshot_ref, explanation_id nullable | **Done** | Composite FK to `forecast_version(forecast_version_id, as_of_date)`; `test_decision_session_fk_chain` |
| AC-5 | `outcome`: UNIQUE `session_id`; validation_status pending/validated/rejected | **Done** | `outcome_validation_status` enum + `test_one_outcome_per_session` |

---

## Definition of Done

| DoD item | Status | Evidence |
|----------|--------|----------|
| End-to-end insert: context → session → recommendation_version | **Done** | `test_decision_session_fk_chain` |
| `recommendation_confidence` separate from `forecast_confidence` | **Done** | Distinct column; test asserts 0.58 ≠ 0.80 horizon confidence (TDS-009 §7) |

---

## Deliverables

| Artifact | Path |
|----------|------|
| Migration | `backend/app/persistence/migrations/versions/0008_decision_stack.py` |
| ORM | `backend/app/persistence/models/decision.py` |
| Repositories | `backend/app/persistence/repositories/decision.py` |
| Validation | `backend/app/persistence/validation/decision.py` |
| Tests | `tests/unit/test_decisions.py` |
| UoW wiring | `backend/app/persistence/unit_of_work.py` |
| Alembic chain / fixture updates | `tests/conftest.py`, `tests/unit/test_alembic_revision_chain.py`, `tests/integration/test_alembic_migrations.py` |

---

## Schema Notes

### Partitioning

| Table | Strategy |
|-------|----------|
| `decision_session` | Quarterly RANGE on `created_at`; child `2026_q2` (Apr–Jun) + DEFAULT |
| `user_context`, `recommendation`, `recommendation_version`, `outcome` | Not partitioned |

Composite PK on `decision_session (session_id, created_at)` required for partitioning. Child tables `recommendation` and `outcome` carry `session_created_at` for FK integrity.

### Confidence separation (TDS-009 §7)

| Field | Table | Semantics |
|-------|-------|-----------|
| `forecast_confidence` | `forecast_version` horizon JSON | Model/forecast trust |
| `recommendation_confidence` | `recommendation_version` | Decision output trust — **separate column** |

### Immutability

- `RecommendationVersionRepository` extends `ImmutableVersionRepository` — `update()` raises `ImmutableVersionUpdateError`.
- New session or supersede = new INSERT; never UPDATE delivered numeric fields.

---

## Tests

| Test | Type | Status |
|------|------|--------|
| `test_action_type_enum_rejects_invalid_value` | Unit | **Pass** |
| `test_recommendation_confidence_bounds_rejects_above_one` | Unit | **Pass** |
| `test_recommendation_version_immutable` | Unit | **Pass** |
| `test_decision_session_fk_chain` | Integration | **Pass** (with `DATABASE_URL`) |
| `test_one_outcome_per_session` | Integration | **Pass** (with `DATABASE_URL`) |

**Total S07 tests:** 5

---

## Traceability

REQ-040, REQ-041, REQ-090, REQ-110 | FD-015, FD-016, FD-023 | TDS-006 §3.12–3.16 | ADR-002

---

*End of E-01-S07 completion report.*
