# E-04 Futures Completion Report — Futures Signal Generator (Prototype)

**Date:** 2026-06-04  
**Story:** E-04 F-04-05 — Futures Signal Generator (PI10 Track A)  
**Epic:** E-04 Domain Agents (Deterministic)  
**Prerequisites:** PI9 Track C (`0012_signal_pi9_contract`); DS-001 downgrade **FOUNDER APPROVED** (production blocker only)  
**Specification:** [SIGNAL_ENGINE_V1.md](../research/SIGNAL_ENGINE_V1.md) §6, [FUTURES_SIGNAL_PROTOTYPE.md](../research/FUTURES_SIGNAL_PROTOTYPE.md) §7.3

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| FuturesObservation model + migration? | **Yes** — `0013_futures_observations`, append-only repo |
| NCDEX public EOD UDiFF bhav parser (KAPAS/SHANKRKPAS)? | **Yes** |
| FuturesSignalGenerator with four transforms? | **Yes** — `curve_slope`, `basis_futures_spot`, `open_interest_change`, `curve_regime` |
| StructuredSignal + SignalSnapshot persist? | **Yes** — Track C repos (Market/Weather pattern) |
| Prototype guardrails (G-01–G-04)? | **Yes** — `environment=prototype`, `futures_feed_ok=false`, confidence ≤ 0.35, `ncdex_public_bhav_prototype` |
| LangGraph / LLM / forecast / decision? | **No** — out of scope |
| Replayable / deterministic? | **Yes** — unit-tested identical re-runs |

**Overall:** **PASS** — PI10 Track A E-04 Futures prototype deliverable complete.

---

## 2. Generator

| Item | Value |
|------|-------|
| Package path | `backend/app/services/signals/futures/` |
| Entry class | `FuturesSignalGenerator` |
| Agent version | `futures-v1.0.0-prototype` |
| Contract model | `shared.signal_contract.models.StructuredSignal` |
| Ingest parser | `backend/app/services/ingest/ncdex/parser.py` |

### 2.1 Emitted signal components

| # | Component | Transform |
|---|-----------|-----------|
| 1 | `curve_slope` | `(P_near − P_far) / P_near` on ₹/quintal settles |
| 2 | `basis_futures_spot` | `(P_futures,near − P_spot) / P_spot` vs Agmarknet modal |
| 3 | `open_interest_change` | Session ΔOI z-scored over 20d near-month OI |
| 4 | `curve_regime` | `backwardation` / `contango` / `flat` (G-07: `curve_regime_mi_eligible=false`) |

Metadata in every signal: `environment=prototype`, `futures_feed_ok=false`, `source=ncdex_public_bhav_prototype`.

### 2.2 Persistence flow

1. `FuturesObservationRepository.insert_observation` — append-only NCDEX EOD rows  
2. `StructuredSignalRepository.insert_signal` — one Futures row per commodity/day/registry  
3. `SignalSnapshotRepository.insert_snapshot` — PI9 contract JSONB + deterministic `snapshot_hash`

---

## 3. Deliverables

| Artifact | Path |
|----------|------|
| ORM model | `backend/app/persistence/models/futures.py` |
| Migration | `backend/app/persistence/migrations/versions/0013_futures_observations.py` |
| Repository | `backend/app/persistence/repositories/futures.py` |
| Validation | `backend/app/persistence/validation/futures.py` |
| NCDEX parser | `backend/app/services/ingest/ncdex/parser.py` |
| Generator | `backend/app/services/signals/futures/generator.py` |
| Feature math | `backend/app/services/signals/futures/features.py` |
| Observation loader | `backend/app/services/signals/futures/observations.py` |
| Constants | `backend/app/services/signals/futures/constants.py` |
| UDiFF fixture | `tests/fixtures/ncdex/udiff_kapas_sample.csv` |
| Test fixtures | `tests/fixtures/futures_signals.py` |
| Parser tests | `tests/unit/test_ncdex_bhav_parser.py` |
| Generator tests | `tests/unit/test_futures_signal_generator.py` |

---

## 4. Tests

| Test module | Count | Scope |
|-------------|-------|-------|
| `test_ncdex_bhav_parser.py` | **5** | UDiFF CSV parse, KAPAS filter, quintal conversion, determinism |
| `test_futures_signal_generator.py` | **7** | curve_slope, confidence cap, near/far, four components, guardrails, replay, persist hash |
| **Futures subtotal** | **12** | |

---

## 5. Quality Gates

| Check | Result |
|-------|--------|
| `uv run ruff check .` | **PASS** |
| `uv run mypy` | **PASS** (198 source files) |
| `uv run pytest tests/ -q` | **PASS** — 221 passed, 63 skipped (no `DATABASE_URL`) |

---

## 6. Guardrails (FUTURES_SIGNAL_PROTOTYPE §7.3)

| ID | Guardrail | Implementation |
|----|-----------|----------------|
| G-01 | `environment=prototype` | `FuturesObservationModel.environment`, `signal_components.environment` |
| G-02 | `futures_feed_ok=false` | `signal_components.futures_feed_ok`, DQS default in `snapshot_service` |
| G-03 | Confidence cap ≤ 0.35 | `CONFIDENCE_CAP_PROTOTYPE = 0.35` |
| G-04 | `source=ncdex_public_bhav_prototype` | Observation source + signal_components |
| G-07 | No production `CURVE_BACKWARDATION` | `curve_regime_mi_eligible=false` always |

---

## 7. Reference Return Values (PI10 Track A)

| Item | Value |
|------|-------|
| Generator path | `backend/app/services/signals/futures/generator.py` |
| Migration path | `backend/app/persistence/migrations/versions/0013_futures_observations.py` |
| Parser path | `backend/app/services/ingest/ncdex/parser.py` |
| Signal components emitted | `curve_slope`, `basis_futures_spot`, `open_interest_change`, `curve_regime` |
| Futures unit test count | **12** |
| Signals generated (unit harness) | **1** StructuredSignal per `generate()` / `generate_and_persist()` call |
| Report path | `docs/reviews/E04_FUTURES_COMPLETION_REPORT.md` |

---

*End of E-04 Futures completion report — PI10 Track A.*
