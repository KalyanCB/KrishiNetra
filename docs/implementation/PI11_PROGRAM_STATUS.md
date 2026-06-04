# PI11 Program Status — Forecast Model Baseline

| Field | Value |
|-------|-------|
| **Increment** | PI11 — Forecast model baseline (training, rolling validation, feature importance, quality service, model registry; Tracks A–F) |
| **Date** | 2026-06-04 |
| **Baseline** | `2fb4e5b` — PI10 forecast foundation and signal completion |
| **HEAD migration chain** | `0001` → `0014_pi10_head_merge` → `0015_forecast_quality_metric` → `0016_forecast_model_registry` |
| **Working tree @ merge** | PI11 Tracks A–F + synthesis handoff |
| **Synthesized by** | KDO PI11 final synthesis (merge gate) |

---

## 1. Track Summary

| Track | Scope | Deliverable | @ disk | Status |
|-------|-------|-------------|--------|--------|
| **A** | Baseline forecast models — `ForecastTrainingDataset` @ 30d; Naive / Linear Regression / Random Forest; MAE, RMSE, MAPE | [FORECAST_BASELINE_REPORT.md](../reviews/FORECAST_BASELINE_REPORT.md) | **Yes** | **COMPLETE** |
| **B** | Time-series validation — rolling-window (no random splits); leakage guards | [TIME_SERIES_VALIDATION_REPORT.md](../reviews/TIME_SERIES_VALIDATION_REPORT.md) | **Yes** | **COMPLETE** |
| **C** | Feature importance — RF baseline; rank Market / Weather / Futures by `feature_lineage` | [FEATURE_IMPORTANCE_REPORT.md](../reviews/FEATURE_IMPORTANCE_REPORT.md) | **Yes** | **COMPLETE** |
| **D** | `ForecastQualityService` — MAE, RMSE, MAPE, Coverage; persist metrics | [FORECAST_QUALITY_REPORT.md](../reviews/FORECAST_QUALITY_REPORT.md) | **Yes** | **COMPLETE** |
| **E** | `ForecastModelRegistry` — version, training window, metrics, feature set id/hash | [MODEL_REGISTRY_REPORT.md](../reviews/MODEL_REGISTRY_REPORT.md) | **Yes** | **COMPLETE** |
| **F** | Program dashboard + metrics framework | PI11_PROGRAM_STATUS.md (this file) | **Yes** | **COMPLETE** |

**Inherited (PI10, @ baseline `2fb4e5b`):** Market + Weather + Futures (`FuturesSignalGenerator` prototype) generators; `ForecastFeatureSnapshot`; `ForecastDatasetBuilder` 30/60/90d export (**120/90/60** fixture rows); [SIGNAL_EFFECTIVENESS_REPORT.md](../reviews/SIGNAL_EFFECTIVENESS_REPORT.md); migration head `0014_pi10_head_merge`; E-05 **ALLOWED (enhanced degraded)**; E-06 forecast **models** not started @ PI10 stop rule.

**PI11 stop rule (honored):** No **decision engine**, **recommendation engine**, **LLM agents**, or **user-facing forecast API**. Focus exclusively on measurable forecast accuracy (baselines + validation + registry). E-06 **decision/runtime** and **LLM** paths remain out of scope.

**Synthesis:** `BaselineHandoffService` wires `data/forecast_models/baseline_metrics.json` into Track D quality rows and Track E registry entries (`train_forecast_baselines.py --sync-services` when `DATABASE_URL` set).

---

## 2. Program Metrics

### 2.1 Observation count (@ PI10 baseline — unchanged @ PI11 merge)

| Layer | Count | Evidence | PI11 delta |
|-------|-------|----------|------------|
| **Agmarknet validated** | **61,544** | 60,445 price + 1,099 arrival @ `@5433` | Unchanged |
| **Weather (NASA POWER)** | **5,620+** | 5 TG belt regions | Unchanged |
| **Futures observations** | **0** (ingest ops TBD) | Generator degraded until NCDEX bhav rows loaded | Unchanged |
| **Policy observations** | **2** | Cotton MSP + export-ban seed stubs | Unchanged |

### 2.2 Signal count (PI10 baseline — unchanged)

| Metric | @ PI10 baseline | @ PI11 merge | Notes |
|--------|-----------------|--------------|-------|
| **Structured signal agents (runtime)** | **3** | **3** | Market + Weather + Futures prototype |
| **Feature signals per agent** | **4** each | **4** each | Unchanged contract |
| **Signal coverage ratio** | **0.7500** (3/4) | **0.7500** | Policy agent still optional |
| **Required coverage ratio** | **1.0000** | **1.0000** | Futures degraded (`futures_feed_ok=false`) |

### 2.3 Forecast dataset size (PI10 baseline — unchanged)

| Horizon | Rows (feature + target pairs) | Coverage | PI11 primary |
|---------|------------------------------|----------|--------------|
| **30d** | **120** | **1.0000** | **Primary** — Track A/B training & validation |
| **60d** | **90** | **1.0000** | Secondary |
| **90d** | **60** | **1.0000** | Secondary |

**Leakage rule (inherited):** `observed_at` post-horizon only — enforced in Track B rolling windows (**PASS**).

### 2.4 Forecast baseline metrics (PI11 @ fixture rolling OOS)

| Model | MAE (INR) | RMSE (INR) | MAPE (%) | OOS n | Status |
|-------|-----------|------------|----------|-------|--------|
| **Naive persistence** | **450.00** | **450.00** | **5.7812** | 60 | **COMPLETE** (Track A) |
| **Linear regression** | **0.00** ⚠️ | **0.00** | **0.00** | 60 | **COMPLETE** — fixture synthetic; not E-06 production evidence |
| **Random forest** | **164.30** | **185.68** | **2.0981** | 60 | **COMPLETE** — best meaningful baseline @ fixture |
| **Best @ 30d (RMSE)** | linear (0) | — | — | — | **Misleading on fixture** — use RF for E-06 iterate planning |

**Artifacts:** `data/forecast_models/baseline_metrics.json`; joblib under `data/forecast_models/30d/`.

### 2.5 Feature importance (PI11 @ fixture RF)

| Group | Aggregate importance | Top feature | Status |
|-------|---------------------|-------------|--------|
| **Market** | **0.3770** | `market.magnitude` | **COMPLETE** (Track C) |
| **Futures** | **0.3667** | `futures.components.basis_futures_spot` | **COMPLETE** |
| **Weather** | **0.2563** | `weather.value` | **COMPLETE** |

**Ranking:** Market > Futures > Weather (fixture panel, seed **42**).

### 2.6 Forecast quality & registry (PI11)

| Service / artifact | Metric / field | @ merge | Status |
|--------------------|----------------|---------|--------|
| **ForecastQualityService** | MAE, RMSE, MAPE, Coverage | Persisted via handoff + unit tests | **COMPLETE** (Track D) |
| **ForecastModelRegistry** | version, training window, metrics, feature set hash | 3 baseline rows @ handoff | **COMPLETE** (Track E) |
| **Migration head** | `0016_forecast_model_registry` | `@5433` upgrade **PASS** | **COMPLETE** |
| **BaselineHandoffService** | `baseline_metrics.json` → D + E | `backend/app/services/forecast/baseline_handoff.py` | **COMPLETE** |

### 2.7 E-05 / E-06 gates (forecast accuracy lens)

| Dimension | PI10 @ baseline | PI11 @ merge |
|-----------|-----------------|--------------|
| **Labeled forecast datasets** | **READY** | **READY** |
| **Baseline forecast models** | None | **READY (fixture)** — `@5433` retrain **TBD** |
| **Feature importance evidence** | Signal effectiveness only | **READY** (RF fixture) |
| **Forecast quality persistence** | Feature store only | **READY** (`0015` + handoff) |
| **Model registry** | `forecast_version` @ `0007` only | **READY** (`0016` + 3 baselines) |
| **E-05 production MI publish** | **BLOCKED** | **BLOCKED** |
| **E-06 decision / LLM / user API** | **NOT STARTED** | **NOT STARTED** (stop rule) |
| **E-06 forecast engine (accuracy gate)** | **NOT STARTED** | **ITERATE** — [PI11_EXECUTIVE_SUMMARY.md](../reviews/PI11_EXECUTIVE_SUMMARY.md) |

---

## 3. Health

| Area | Status | Notes |
|------|--------|-------|
| **E-01 data foundation** | Green | Baseline `2fb4e5b`; PI10 corpus @ `@5433` |
| **E-04 signal runtime** | Green | 3 agents; replay PASS @ PI10 |
| **E-05 MI (production)** | Yellow | Engineering allowed (degraded); publish **BLOCKED** |
| **PI11 forecast baselines** | Green | Tracks A–F **COMPLETE** on fixture |
| **E-06 decision / LLM** | Green (gated) | **Out of scope** — stop rule honored |
| **E-06 forecast models** | Yellow | **ITERATE** — real-corpus validation required |
| **E-03 ops** | Yellow | Live OGD blocked; NCDEX bhav ingest ops TBD |
| **Governance** | Yellow | DS-001 OPTION B **OPEN** |
| **Git / CI** | Green | Gates **PASS** @ merge (see §8) |

---

## 4. Blockers

| Blocker | Blocks | Does not block |
|---------|--------|----------------|
| **Fixture-only baseline metrics** | E-06 **PROCEED** (production forecast) | PI11 merge; internal registry/quality |
| **Linear 0-error on fixture** | Trusting linear as production winner | RF + naive as honest error band |
| **DS-001 production path (OPTION B unsigned)** | Production MI, licensed futures | PI11 sklearn baselines on fixture / `@5433` retrain |
| **No user-facing forecast API (stop rule)** | Product MI publish | Internal metrics + registry |
| **NCDEX bhav rows @ 5433** | Non-neutral Futures on integration DB | Fixture training panels |
| **E-06 decision / recommendation / LLM** | Decision runtime, recommendations, agents | Forecast accuracy research @ PI11 |

---

## 5. Dependencies

| Upstream | Downstream | Status |
|----------|------------|--------|
| PI10 datasets + feature store | Track A `ForecastTrainingDataset` | **Done** |
| PI10 30d export | Track A training; Track B rolling validation | **Done** |
| Track A RF baseline | Track C feature importance | **Done** |
| Track B validation spec | Track A held-out evaluation | **Done** |
| Tracks A metrics JSON | Track D + E via `BaselineHandoffService` | **Done** |
| Tracks A–E complete | PI11_EXECUTIVE_SUMMARY.md | **Done** |

---

## 6. Critical Path

```mermaid
flowchart LR
  PI10[PI10 COMPLETE 2fb4e5b] --> PI11[PI11 COMPLETE]
  PI11 --> E06I[E-06 ITERATE]
  E06I --> DB[@5433 retrain]
  DB --> BHAV[NCDEX bhav ingest]
  BHAV --> E06P[E-06 PROCEED TBD]
```

| Priority | Item | Owner |
|----------|------|-------|
| **P0** | `@5433` baseline retrain + compare fixture MAPE | Post-PI11 |
| **P1** | NCDEX bhav ingest ops | E-03 |
| **P2** | E-06 accuracy thresholds on real panel | E-06 research |
| **P3** | DS-001 OPTION B (production) | Founder |

**Do not start @ PI11 scope:** Decision engine, recommendation engine, LLM agents, user-facing forecast API (stop rule).

---

## 7. Risks

| ID | Risk | Severity | Mitigation |
|----|------|----------|------------|
| **R-01** | Random train/test split leakage | High | Track B — rolling windows only; **PASS** |
| **R-02** | Fixture panel ≠ live corpus | High | Executive summary **ITERATE**; `@5433` retrain queued |
| **R-03** | Linear 0-error misread as production win | High | Call out in PI11 exec summary; promote RF for planning |
| **R-04** | Futures feature degeneracy (empty bhav) | Medium | Track C ranks; degraded generator guardrails |
| **R-05** | Over-interpreting baseline MAPE | Medium | E-06 gates on real evidence |
| **R-06** | Scope creep into E-06 decision/LLM | High | **Stop rule** honored |

---

## 8. Quality Gates

| Gate | PI10 @ `2fb4e5b` | PI11 @ merge |
|------|------------------|--------------|
| `pytest` (no `DATABASE_URL`) | **222 passed**, 63 skipped | **278 passed**, 66 skipped, **0 failed** |
| `pytest` + `DATABASE_URL` @ 5433 | **280 passed**, 5 skipped | **339 passed**, 5 skipped, **0 failed** |
| Forecast dataset reproducibility (`--fixture`) | **PASS** | **PASS** — 120/90/60 rows |
| Rolling validation leakage tests | N/A | **PASS** (14 tests) |
| Baseline reproducibility (deterministic seed) | N/A | **PASS** (12 tests) |
| Baseline handoff (D/E wiring) | N/A | **PASS** (7 tests) |
| `ruff check` / `mypy` | **Pass** | **Pass** |
| `alembic upgrade head` | `0014_pi10_head_merge` | **Pass** — `0016_forecast_model_registry` |

**PI11 new tests:** **59** (12 + 14 + 10 + 8 + 8 + 7).

---

## 9. PI11 Deliverable Checklist

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | FORECAST_BASELINE_REPORT + baseline models @ 30d | **COMPLETE** |
| 2 | TIME_SERIES_VALIDATION_REPORT + `rolling.py` | **COMPLETE** |
| 3 | FEATURE_IMPORTANCE_REPORT + importance script | **COMPLETE** |
| 4 | FORECAST_QUALITY_REPORT + `ForecastQualityService` | **COMPLETE** |
| 5 | MODEL_REGISTRY_REPORT + `ForecastModelRegistry` | **COMPLETE** |
| 6 | PI11_PROGRAM_STATUS.md | **COMPLETE** |
| 7 | PI11_EXECUTIVE_SUMMARY.md | **COMPLETE** |
| 8 | Track A → D/E `BaselineHandoffService` | **COMPLETE** |

**Recommendation @ merge:** **COMPLETE PI11** — **ITERATE E-06** on real data — **BLOCKED** E-06 decision/LLM/user API (stop rule).

---

## 10. References

| Doc | Role |
|-----|------|
| [PI10_PROGRAM_STATUS.md](./PI10_PROGRAM_STATUS.md) | Prior increment dashboard |
| [PI10_EXECUTIVE_SUMMARY.md](../reviews/PI10_EXECUTIVE_SUMMARY.md) | PI10 close verdict |
| [PI11_EXECUTIVE_SUMMARY.md](../reviews/PI11_EXECUTIVE_SUMMARY.md) | PI11 close verdict |
| [FORECAST_DATASET_REPORT.md](../reviews/FORECAST_DATASET_REPORT.md) | 30/60/90d builder |
| [FORECAST_FEATURE_STORE_REPORT.md](../reviews/FORECAST_FEATURE_STORE_REPORT.md) | Feature assembly |
| [FORECAST_RESEARCH_DESIGN.md](../research/FORECAST_RESEARCH_DESIGN.md) | Horizons 30/60/90 |
| [DS001_FOUNDER_DECISION_PACKAGE.md](../research/DS001_FOUNDER_DECISION_PACKAGE.md) | Production blocker |

---

*End of PI11 program status — merged @ 2026-06-04.*
