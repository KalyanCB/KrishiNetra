# PI12 Program Status — Real Corpus Forecast Validation

| Field | Value |
|-------|-------|
| **Increment** | PI12 — Real `@5433` dataset audit, expansion, baseline retrain, leakage audit, E-06 readiness gate (Tracks A–E) |
| **Date** | 2026-06-04 |
| **Baseline** | `c64fe65` — PI11 forecast model baseline |
| **HEAD migration chain** | `0001` → `0016_forecast_model_registry` (unchanged) |
| **Working tree @ merge** | PI12 Tracks A–E + synthesis |
| **Synthesized by** | KDO PI12 final synthesis (merge gate) |

---

## 1. Track Summary

| Track | Scope | Deliverable | @ disk | Status |
|-------|-------|-------------|--------|--------|
| **A** | Real corpus audit — fixture vs `@5433` row counts, observation funnel, leakage notes | [REAL_DATASET_AUDIT.md](../reviews/REAL_DATASET_AUDIT.md) | **Yes** | **COMPLETE** |
| **B** | Real dataset expansion — `real_` JSONL export; ≥1,000 @ 30d | [REAL_DATASET_EXPANSION_REPORT.md](../reviews/REAL_DATASET_EXPANSION_REPORT.md) | **Yes** | **COMPLETE** |
| **C** | Real baseline retrain — naive / linear / RF on `real_forecast_target_30d.jsonl` | [REAL_FORECAST_BASELINE_REPORT.md](../reviews/REAL_FORECAST_BASELINE_REPORT.md) | **Yes** | **COMPLETE** (metrics **inconclusive**) |
| **D** | Leakage audit — PI11 linear 0-error root cause | [LEAKAGE_AUDIT_REPORT.md](../reviews/LEAKAGE_AUDIT_REPORT.md) | **Yes** | **COMPLETE** — **`LEAKAGE_NO`** |
| **E** | E-06 readiness gate — Tier-0/Tier-1 accuracy prerequisites | [E06_READINESS_GATE.md](../research/E06_READINESS_GATE.md) | **Yes** | **COMPLETE** — **ITERATE** |
| **F** | Program dashboard + executive summary | PI12_PROGRAM_STATUS.md (this file) | **Yes** | **COMPLETE** |

**Inherited (PI11 @ `c64fe65`):** Fixture baselines (naive **450** INR MAE; RF **164.3** INR); rolling validation; feature importance; quality service; model registry; `BaselineHandoffService`; PI11 stop rule (no decision / recommendation / LLM / user forecast API).

**PI12 stop rule (honored):** No **decision engine**, **recommendation engine**, **LLM agents**, or **user-facing forecast API**. E-06 **runtime** and **LLM** paths remain out of scope.

**Code / script deltas:** `--filename-prefix real_` on `build_forecast_datasets.py`; `--real` on `train_forecast_baselines.py`; `target_log_return` on export rows; `test_fixture_leakage_audit.py` (5 tests); real-corpus tests in `test_forecast_baseline_models.py`.

---

## 2. Program Metrics

### 2.1 Observation count (@5433 — Track A)

| Layer | Count | Evidence | PI12 delta |
|-------|-------|----------|------------|
| **Agmarknet validated** | **61,547** | 60,448 price + 1,099 arrival | +3 vs PI10/PI11 cite |
| **Weather (NASA POWER)** | **8,170** | 5 TG belt regions | Unchanged ingest |
| **Futures observations** | **0** | NCDEX bhav not loaded | Unchanged |
| **Policy observations** | **2** | Cotton MSP + export-ban stubs | Unchanged |
| **Signal snapshots (cotton)** | **0** | No PI9 backfill @5433 | **Blocks P0-6** |

### 2.2 Forecast dataset size (fixture vs real)

| Horizon | Fixture (`--fixture`) | Real `@5433` (default window) | PI12 primary |
|---------|----------------------|------------------------------|--------------|
| **30d** | **120** | **1069** | **Primary** — Track B/C/E |
| **60d** | **90** | **1039** | Informational |
| **90d** | **60** | **1009** | Informational |

**Basket modal dates:** **1,100** (daily **2023-06-01** → **2026-06-04**); **100%** horizon coverage inside default window.

**Funnel (validated → supervised):** **20,882** validated modal price rows → **1,100** basket dates → **1069** labeled 30d rows. **1,099** arrival rows **not** consumed by `ForecastDatasetBuilder`.

**Exports:** `data/forecast_datasets/real_forecast_target_{30,60,90}d.jsonl` via `--filename-prefix real_`.

### 2.3 Real baseline metrics @ 30d (Track C — rolling OOS)

| Model | MAE (INR) | RMSE (INR) | MAPE (%) | OOS n | Status |
|-------|-----------|------------|----------|-------|--------|
| **Naive persistence** | **0.00** | **0.00** | **0.00** | 1000 | **Inconclusive** — target ≡ spot |
| **Linear regression** | **0.00** | **0.00** | **0.00** | 1000 | **Inconclusive** |
| **Random forest** | **0.00** | **0.00** | **0.00** | 1000 | **Inconclusive** |
| **beats_naive (RMSE)** | — | — | — | — | **NO** (0 vs 0 tie) |

**Artifacts:** `data/forecast_models/real_30d/baseline_metrics.json`; joblib under `data/forecast_models/real_30d/`.

**Degenerate target note:** On `@5433`, basket modal takes only **two** levels (**9,665** and **10,000** INR) with **one** day-over-day change in **1,100** dates — so ∀T in export window: `modal(T+30) = modal(T)`. This is **flat-corpus stickiness**, not PI11 fixture affine law (`y = spot + 450`).

### 2.4 Leakage verdict (Track D)

| Verdict | Mechanism |
|---------|-----------|
| **`LEAKAGE_NO`** | Target ∉ feature matrix; rolling train≺test; Track B embargo **PASS** on fixture |
| **PI11 linear 0-error** | Fixture physics: `y = spot + 450` @ 30d |
| **PI12 real 0-error** | Flat modal series — **not** label leakage |

### 2.5 E-06 readiness (Track E)

| Tier | Result |
|------|--------|
| **Tier-0 (evaluation validity)** | **NOT MET** — P0-3, P0-4, P0-5 (data), P0-6 |
| **Tier-1 (TDS-000 KPIs)** | **NOT EVALUATED** |
| **Corpus scale (≥500 @30d)** | **PASS** — **1069** |
| **Leakage** | **PASS** — `LEAKAGE_NO` |
| **E-06 accuracy-gated PROCEED** | **BLOCKED** |
| **Program verdict** | **ITERATE** |

---

## 3. Health

| Area | Status | Notes |
|------|--------|-------|
| **E-01 data foundation** | Yellow | Volume OK; **flat modal ladder** on `@5433` blocks informative TY-01 |
| **E-04 signal runtime** | Green | PI9 generators; **0** snapshots on DB for forecast features |
| **E-05 MI (production)** | Yellow | Engineering allowed (degraded); publish **BLOCKED** |
| **PI12 real corpus pipeline** | Green | Export + retrain + leakage tests **COMPLETE** |
| **PI12 forecast accuracy evidence** | Red | All OOS metrics **0** — ranking **inconclusive** |
| **E-06 decision / LLM** | Green (gated) | **Out of scope** — stop rule honored |
| **E-06 forecast models** | Red | **ITERATE** — fix P0-3..P0-6 per E06 gate |
| **E-03 ops** | Yellow | Live OGD + NCDEX bhav ingest TBD |
| **Governance** | Yellow | DS-001 OPTION B **OPEN** |
| **Git / CI** | Green | Gates **PASS** @ merge (see §8) |

---

## 4. Blockers

| Blocker | Blocks | Does not block |
|---------|--------|----------------|
| **target_price_level ≡ spot_price_level @5433** | E-06 **PROCEED**; `beats_naive`; Tier-1 KPI scoring | PI12 merge; pipeline proof |
| **Flat basket modal (2 levels / 1100 days)** | Trusting real baseline MAPE/RMSE | Leakage methodology; row-count gate |
| **0 signal_snapshot @5433** | P0-6 feature depth | Spot-only baseline train (degenerate) |
| **DS-001 OPTION B unsigned** | Production MI, licensed futures | Internal research |
| **E-06 decision / LLM / user API (stop rule)** | Decision runtime, recommendations, agents | Dataset export + leakage audit |
| **NCDEX bhav @5433** | Non-neutral Futures features | Price-level TY-01 (when corpus varies) |

---

## 5. Dependencies

| Upstream | Downstream | Status |
|----------|------------|--------|
| PI11 baselines + rolling spec | Track C `--real` retrain | **Done** |
| PI10 `ForecastDatasetBuilder` | Tracks A/B export | **Done** |
| Track A audit | Track B expansion target proof | **Done** |
| Track B `real_` JSONL | Track C baselines | **Done** |
| Track D leakage | Track E gate §3 P0-2 | **Done** |
| Tracks A–E | PI12_EXECUTIVE_SUMMARY.md | **Done** |

---

## 6. Critical Path

```mermaid
flowchart LR
  PI11[PI11 COMPLETE c64fe65] --> PI12[PI12 COMPLETE]
  PI12 --> E06I[E-06 ITERATE]
  E06I --> P03[Fix P0-3 targets / corpus]
  P03 --> OGD[SR-01 live OGD variation]
  OGD --> SNAP[signal_snapshot backfill]
  SNAP --> REGATE[Re-issue E06 gate]
  REGATE --> E06P[E-06 PROCEED TBD]
```

| Priority | Item | Owner |
|----------|------|-------|
| **P0** | Export QA: median \|target − spot\| ≥ 50 INR before `--real` train | Post-PI12 |
| **P1** | SR-01 live OGD + validation dispersion (remove flat modal ladder) | E-03 |
| **P2** | Backfill `signal_snapshot`; re-export with ≥3 numerics | E-04 / ops |
| **P3** | Re-run `--real` baselines; require `beats_naive` **YES** | E-06 research |
| **P4** | DS-001 OPTION B (production) | Founder |

**Do not start @ PI12 scope:** Decision engine, recommendation engine, LLM agents, user-facing forecast API (stop rule).

---

## 7. Risks

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| **R-01** | Promoting 0 MAE real baselines as production win | High | E06 gate **ITERATE**; call out flat modal in exec summary |
| **R-02** | Conflating PI11 fixture 0-error with PI12 real 0-error | High | Track D vs flat-corpus stickiness (distinct mechanisms) |
| **R-03** | `observed_at` not enforced in builder | Medium | Track A noted; enforce when late revisions appear |
| **R-04** | No signal features on real export | Medium | P0-6; snapshot backfill |
| **R-05** | Integration DB pollution (registry FK tests) | Low | Optional `@5433` pytest; CI uses no-DB path |
| **R-06** | Scope creep into E-06 decision/LLM | High | **Stop rule** honored |

---

## 8. Quality Gates

| Gate | PI11 @ `c64fe65` | PI12 @ merge |
|------|------------------|--------------|
| `pytest` (no `DATABASE_URL`) | **278 passed**, 66 skipped | **287 passed**, 66 skipped, **0 failed** |
| `pytest` + `DATABASE_URL` @ 5433 | **339 passed**, 5 skipped | **Not required** — 2 registry FK failures (DB state); PI12 delta tests pass without DB |
| `ruff check` | **Pass** | **Pass** |
| `mypy` (`forecasting`, scripts) | **Pass** | **Pass** |
| Fixture dataset rebuild (`--fixture`) | **PASS** — 120/90/60 | **PASS** — unchanged |
| Real dataset rebuild (`--filename-prefix real_`) | N/A | **PASS** — **1069/1039/1009** |
| Leakage audit tests | N/A | **PASS** — 5 tests (`test_fixture_leakage_audit.py`) |
| Real baseline train (`--real --write-report`) | N/A | **PASS** — artifacts + report |
| E-06 decision / LLM / user API | **NOT STARTED** | **NOT STARTED** (stop rule) |

**PI12 new tests:** **~9** (5 leakage + ~4 real-corpus in `test_forecast_baseline_models.py`).

---

## 9. PI12 Deliverable Checklist

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | REAL_DATASET_AUDIT.md | **COMPLETE** |
| 2 | REAL_DATASET_EXPANSION_REPORT.md | **COMPLETE** |
| 3 | REAL_FORECAST_BASELINE_REPORT.md | **COMPLETE** |
| 4 | LEAKAGE_AUDIT_REPORT.md | **COMPLETE** |
| 5 | E06_READINESS_GATE.md | **COMPLETE** |
| 6 | PI12_PROGRAM_STATUS.md | **COMPLETE** |
| 7 | PI12_EXECUTIVE_SUMMARY.md | **COMPLETE** |
| 8 | `real_*` JSONL + `real_30d/` artifacts | **COMPLETE** |

**Recommendation @ merge:** **COMPLETE PI12** — **ITERATE E-06** (fix targets/corpus) — **BLOCKED** E-06 PROCEED / decision / LLM / user API (stop rule).

---

## 10. References

| Doc | Role |
|-----|------|
| [PI11_PROGRAM_STATUS.md](./PI11_PROGRAM_STATUS.md) | Prior increment dashboard |
| [PI11_EXECUTIVE_SUMMARY.md](../reviews/PI11_EXECUTIVE_SUMMARY.md) | PI11 close verdict |
| [E06_READINESS_GATE.md](../research/E06_READINESS_GATE.md) | PI12 Track E gate |
| [FORECAST_RESEARCH_DESIGN.md](../research/FORECAST_RESEARCH_DESIGN.md) | TY-01 / TY-04 targets |
| [DS001_FOUNDER_DECISION_PACKAGE.md](../research/DS001_FOUNDER_DECISION_PACKAGE.md) | Production blocker |

---

*End of PI12 program status — merged @ 2026-06-04.*
