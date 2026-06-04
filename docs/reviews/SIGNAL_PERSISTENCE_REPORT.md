# SignalSnapshot Persistence Report — PI9 Track C

**Date:** 2026-06-04  
**PI:** PI9 Track C (KDO — SignalSnapshot persistence)  
**Workspace:** `e9fa355`  
**Prerequisites:** Migration `0006_signals_partitioned` (E-01-S05); head `0011_observation_rejected` (PI8)  
**Specification:** [SIGNAL_ENGINE_V1.md](../research/SIGNAL_ENGINE_V1.md) §2, §8; TDS-006 §3.8–3.9

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| SignalSnapshot persistence operational? | **Yes** — extended `signal_snapshot` + `structured_signal` with PI9 contract |
| Migration required beyond 0006? | **Yes** — `0012_signal_pi9_contract` |
| Append-only enforced? | **Yes** — repository `update()` blocked; insert-only paths |
| Signal runtime (E-04)? | **No** — persistence layer only (Track C scope) |

**Overall:** **PASS** — PI9 Track C deliverable ready for Market/Weather generators (Tracks A/B).

---

## 2. Schema Baseline (0006)

Migration `0006_signals_partitioned` already provides:

| Table | Role |
|-------|------|
| `structured_signal` | Per-agent `StructuredSignal` (partitioned on `as_of_date`) |
| `signal_snapshot` | Daily bundle: `signal_ids`, `snapshot_hash`, optional `data_quality_snapshot_id` |

TDS-006 column names remain on `structured_signal` (`agent_type`, `direction`, `magnitude`, `confidence`, `signal_components`).

---

## 3. PI9 Extension (0012)

**Revision:** `0012_signal_pi9_contract`  
**Revises:** `0011_observation_rejected`

| Change | Table | Column | Purpose |
|--------|-------|--------|---------|
| ADD | `structured_signal` | `trace_id UUID` | Orchestration lineage per agent row |
| ADD | `signal_snapshot` | `trace_id UUID` | DATA_REFRESH / LangGraph fork trace |
| ADD | `signal_snapshot` | `signals JSONB` | Denormalized PI9 contract rows |
| INDEX | `signal_snapshot` | `ix_snapshot_trace_id` | Lookup by `trace_id` |

---

## 4. PI9 Persisted Signal Contract

Each element of `signal_snapshot.signals` stores:

| PI9 field | TDS-006 / ORM source |
|-----------|----------------------|
| `signal_type` | `structured_signal.agent_type` |
| `signal_direction` | `structured_signal.direction` |
| `signal_magnitude` | `structured_signal.magnitude` |
| `signal_confidence` | `structured_signal.confidence` |
| `signal_inputs` | `structured_signal.signal_components` |
| `as_of_date` | `structured_signal.as_of_date` (ISO date string in JSON) |
| `trace_id` | `signal_snapshot.trace_id` (snapshot-level; not duplicated per row) |

`SignalSnapshotRepository.insert_snapshot` normalizes TDS-006 or PI9 keys, sorts by `signal_type`, computes SHA-256 `snapshot_hash` over canonical PI9 JSON (includes `trace_id` when set).

---

## 5. Deliverables

| Artifact | Path |
|----------|------|
| Migration | `backend/app/persistence/migrations/versions/0012_signal_snapshot_pi9_contract.py` |
| ORM | `backend/app/persistence/models/signal.py` |
| Validation / hash | `backend/app/persistence/validation/signal.py` |
| Repositories | `backend/app/persistence/repositories/signal.py` |
| Unit tests | `tests/unit/test_signal_persistence_pi9.py`, `tests/unit/test_signals.py` |

---

## 6. Repository Behavior

| Method | Behavior |
|--------|----------|
| `StructuredSignalRepository.insert_signal` | Validates agent_type, direction, bounds; append-only |
| `SignalSnapshotRepository.insert_snapshot` | Requires `trace_id` (auto-generates UUID if omitted); fills `signals` JSONB; hash |
| `SignalSnapshotRepository.get_snapshot` | `(commodity_id, as_of_date, registry_id)` |
| `SignalSnapshotRepository.get_snapshot_by_trace_id` | Replay / audit lookup |
| `*.update()` | **Blocked** — `ImmutableVersionUpdateError` |

Legacy fixtures may still use `BaseRepository.insert()` without PI9 `signals` / `trace_id`; column defaults (`signals = []`) preserve compatibility.

---

## 7. Tests

| Test module | Unit | Integration (DATABASE_URL) |
|-------------|------|----------------------------|
| `test_signal_persistence_pi9.py` | 7 | — |
| `test_signals.py` | 2 | 3 |
| `test_alembic_revision_chain.py` | 1 (head chain) | — |

**PI9 Track C unit tests:** 7 (`test_signal_persistence_pi9.py`)

---

## 8. Quality Gates

| Check | Result |
|-------|--------|
| `uv run ruff check .` | **PASS** |
| `uv run mypy` | **PASS** (145 source files) |
| `uv run pytest tests/ -q` | **PASS** — 157 passed, 25 skipped (no `DATABASE_URL`) |
| `alembic upgrade head` | Head `0012_signal_pi9_contract` |

---

## 9. Reference Return Values (PI9 Track C)

| Item | Value |
|------|-------|
| Migration revision | `0012_signal_pi9_contract` |
| Model path | `backend/app/persistence/models/signal.py` |
| Repository path | `backend/app/persistence/repositories/signal.py` |
| PI9 unit test count | **7** |
| Report path | `docs/reviews/SIGNAL_PERSISTENCE_REPORT.md` |

---

*End of SignalSnapshot persistence report — PI9 Track C.*
