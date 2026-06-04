# E-04-S01 Completion Report — Market Signal Runtime

**Date:** 2026-06-04  
**Story:** E-04-S01 — Market Signal Runtime (PI9 Track A)  
**Epic:** E-04 Domain Agents (Deterministic)  
**Prerequisites:** PI9 Track C (`0012_signal_pi9_contract`), validated Agmarknet observations  
**Specification:** [SIGNAL_ENGINE_V1.md](../research/SIGNAL_ENGINE_V1.md) §3, [SIGNAL_MATH_SPECIFICATION.md](../research/SIGNAL_MATH_SPECIFICATION.md) §3

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| MarketSignalGenerator implemented? | **Yes** |
| Four deterministic feature signals? | **Yes** — Price Momentum, Arrival Momentum, Price vs MSP Distance, Price Acceleration |
| VALIDATED/PUBLISHED observations only? | **Yes** — `received` / `rejected` excluded |
| StructuredSignal + SignalSnapshot persist? | **Yes** — Track C repos |
| LangGraph / LLM / forecast? | **No** — out of scope |
| Replayable / deterministic? | **Yes** — unit-tested identical re-runs |

**Overall:** **PASS** — PI9 Track A E-04-S01 deliverable complete.

---

## 2. Generator

| Item | Value |
|------|-------|
| Package path | `backend/app/services/signals/market/` |
| Entry class | `MarketSignalGenerator` |
| Agent version | `market-v1.0.0` |
| Contract model | `shared.signal_contract.models.StructuredSignal` |
| Primary market basket | Telangana primary mandis (`load_telangana_primary_market_ids`) |

### 2.1 Emitted signal types (feature components)

| # | `MarketSignalType` | Transform |
|---|-------------------|-----------|
| 1 | `price_momentum` | Z-score of basket modal vs 30d rolling window |
| 2 | `arrival_momentum` | Z-score of basket arrivals; FG-01 Oct–Mar gate |
| 3 | `price_vs_msp_distance` | `(spot − MSP) / MSP`; registry `msp_proximity_pct`; MSP stub `7121` if missing |
| 4 | `price_acceleration` | Second difference of basket modal momentum |

Composite `StructuredSignal` (`agent_type = Market`) aggregates direction (weighted vote), magnitude, confidence, and `value = sign(dir) × m` per SIGNAL_MATH §3.

### 2.2 Persistence flow

1. `StructuredSignalRepository.insert_signal` — one Market row per commodity/day/registry  
2. `SignalSnapshotRepository.insert_snapshot` — PI9 contract JSONB + deterministic `snapshot_hash`

---

## 3. Deliverables

| Artifact | Path |
|----------|------|
| Generator | `backend/app/services/signals/market/generator.py` |
| Feature math | `backend/app/services/signals/market/features.py` |
| Constants | `backend/app/services/signals/market/constants.py` |
| Contract extension | `shared/signal_contract/models.py` (`signal_components`, `source_refs`) |
| Arrival repo list | `backend/app/persistence/repositories/observation.py` |
| Fixtures | `tests/fixtures/market_signals.py` |
| Unit tests | `tests/unit/test_market_signal_generator.py` |

---

## 4. Tests

| Test module | Count | Scope |
|-------------|-------|-------|
| `test_market_signal_generator.py` | **9** | Z-score, season gate, MSP, four components, validated-only filter, replay, persist hash |

---

## 5. Quality Gates

| Check | Result |
|-------|--------|
| `uv run ruff check .` | **PASS** |
| `uv run mypy` | **PASS** (156 source files) |
| `uv run pytest tests/ -q` | **PASS** — 166 passed, 57 skipped (no `DATABASE_URL`) |

---

## 6. Reference Return Values (PI9 Track A)

| Item | Value |
|------|-------|
| Generator path | `backend/app/services/signals/market/generator.py` |
| Signal types emitted | `price_momentum`, `arrival_momentum`, `price_vs_msp_distance`, `price_acceleration` |
| Unit test count | **9** |
| Report path | `docs/reviews/E04_S01_COMPLETION_REPORT.md` |

---

*End of E-04-S01 completion report — PI9 Track A.*
