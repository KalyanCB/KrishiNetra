# PI9 Track D — Signal Replay Validation Report

**Date:** 2026-06-04  
**Story:** PI9 Track D — Signal Replay Harness (Same Inputs = Same Outputs)  
**Tracks validated:** A (MarketSignalGenerator), B (WeatherSignalGenerator), C (SignalSnapshot @ `0012`)  
**Harness:** `backend/app/services/signals/replay/`  
**Tests:** `tests/replay/test_signal_replay.py`

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Replay harness implemented? | **Yes** |
| Same Inputs = Same Outputs proven? | **Yes** — 5 cycles per track |
| Compared signal rows, `snapshot_hash`, structured fields? | **Yes** |
| Fixture + `@5433` integration paths? | **Yes** |
| pytest / ruff / mypy clean? | **Yes** |

**Overall:** **PASS** — PI9 Track D deliverable complete.

---

## 2. Replay configuration

| Parameter | Value |
|-----------|-------|
| Cycles per track | **5** (`DEFAULT_REPLAY_CYCLES`) |
| Market fixture `as_of_date` | `2026-02-15` (arrival season) |
| Weather fixture `as_of_date` | `2026-06-03` |
| Commodity | `cotton` |
| Migration head | `0012_signal_pi9_contract` |

---

## 3. Cycle results

| Track | Generator / contract | Cycles run | Pass/Fail | Comparison scope |
|-------|----------------------|------------|-----------|------------------|
| **A** | `MarketSignalGenerator` | 5 | **PASS** | `structured_signal` fields, PI9 signal row, `snapshot_hash` |
| **B** | `WeatherSignalGenerator` | 5 | **PASS** | `structured_signal` fields, PI9 signal row |
| **C** | Combined `SignalSnapshot` | 5 | **PASS** | `snapshot_hash`, sorted PI9 `signals` JSONB, market + weather structured fields |
| **B (DB)** | Weather @ `127.0.0.1:5433` | 5 | **PASS** | Live `load_observation_series` + fingerprint stability |

All cycles compared cycle 0 baseline via canonical JSON fingerprint (`fingerprint_to_json`).

---

## 4. Reference fingerprints (fixture graph, trace-pinned)

Captured from pinned fixtures (`rising_price_window`, `flat_arrival_window`, `_build_series` rain=`2.5` mm).  
`snapshot_hash` values include `trace_id` per PI9 Track C contract.

| Artifact | Value |
|----------|-------|
| Market `snapshot_hash` (Track A, single-agent payload) | `ebea503204086cad41b0fa496d7b77f101036ca17a120c3a9b02a3e9d9a49f80` |
| Combined `snapshot_hash` (Market + Weather) | `b6d4aece6ec48f4d9b0ec60410677e54474911ba999bb32d95a48c275078f66b` |
| Market composite direction | `bullish` |
| Weather composite direction | `neutral` |

---

## 5. Harness API

| Symbol | Path | Purpose |
|--------|------|---------|
| `run_market_replay` | `backend/app/services/signals/replay/harness.py` | N-cycle Market generator validation |
| `run_weather_replay` | same | N-cycle Weather generator validation |
| `fingerprint_combined_snapshot_from_signals` | same | Track C hash + PI9 rows without DB writes |
| `validate_replay_cycles` | same | Generic N-cycle equality gate |
| `assemble_combined_snapshot` | same | Persist combined snapshot via `SignalSnapshotRepository` |

Structured fields compared (UUIDs excluded): `agent_type`, `commodity_id`, `as_of_date`, `value`, `direction`, `magnitude`, `confidence`, `signal_components`, `source_observation_refs`, `agent_version`.

PI9 persisted row keys validated via `structured_signal_to_persisted_row` → `normalize_signal_payload`.

---

## 6. Quality gates

| Gate | Command | Result |
|------|---------|--------|
| pytest (fixtures) | `pytest tests/replay/test_signal_replay.py` | **4 passed**, 1 skipped (no `DATABASE_URL`) |
| pytest (+ `@5433`) | `DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra pytest tests/replay/` | **8 passed** |
| ruff | `ruff check backend/app/services/signals/replay/ tests/replay/` | **PASS** |
| ruff format | `ruff format --check …` | **PASS** |
| mypy | `mypy backend/app/services/signals/replay/` | **PASS** |

---

## 7. Files added

| Path | Role |
|------|------|
| `backend/app/services/signals/replay/harness.py` | Replay harness core |
| `backend/app/services/signals/replay/__init__.py` | Public exports |
| `tests/replay/test_signal_replay.py` | Track A/B/C + DB integration tests |
| `docs/reviews/SIGNAL_REPLAY_REPORT.md` | This report |

---

## 8. Notes

1. **Observation UUID stability:** Replay cycles must reuse the same in-memory observation lists; regenerating fixtures inside each cycle produces new `source_observation_refs` and correctly fails replay validation.
2. **`trace_id` in `snapshot_hash`:** Per `compute_snapshot_hash`, hash inputs include `trace_id` when set; cross-environment comparisons must pin the same `trace_id`.
3. **E-01 replay chain:** Existing `tests/replay/test_replay_hash_contract.py` (registry + snapshot + formula_version) remains complementary; Track D covers generator determinism upstream of forecast replay.

---

*End of PI9 Track D signal replay report.*
