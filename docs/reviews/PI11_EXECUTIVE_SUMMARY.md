# PI11 Executive Summary — Forecast Model Baseline

**Date:** 2026-06-04  
**Synthesized by:** KDO PI11 final synthesis (merge gate)  
**Baseline (pre-PI11):** `2fb4e5b` — PI10 forecast foundation and signal completion  
**Migration head @ merge:** `0016_forecast_model_registry`  
**Recommendation:** **ITERATE E-06** — baseline + registry **COMPLETE** on fixture; **BLOCKED** decision/LLM/user API (stop rule)

---

## 1. Executive Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | **Can cotton prices be forecast?** | **Yes — prototype evidence on PI10 fixture panel** — 30d TY-01 baselines train and produce finite rolling OOS errors (naive MAE **450** INR; RF MAE **164.3** INR). **Not proven on live `@5433` corpus** yet. |
| 2 | **Which model performs best?** | **Rolling OOS @ 30d (fixture):** `linear_regression` reports **0** MAE/RMSE/MAPE — **synthetic** (deterministic fixture + low feature count). **Best meaningful baseline:** `random_forest` (MAE **164.3**, RMSE **185.7**, MAPE **2.10%**, n=**60**). `naive_persistence`: MAE **450**, MAPE **5.78%**. |
| 3 | **Which features matter most?** | **Market > Futures > Weather** on RF Gini aggregates — Market **0.377**, Futures **0.367**, Weather **0.256**; top singles: `market.magnitude`, `futures.components.basis_futures_spot`, `weather.value` ([FEATURE_IMPORTANCE_REPORT](./FEATURE_IMPORTANCE_REPORT.md)). |
| 4 | **Is forecast accuracy sufficient for E-06?** | **No — not yet.** Fixture metrics do not meet a production E-06 accuracy bar; linear **0-error** must not be promoted. Need `@5433` retrain, live futures bhav, and MAPE/RMSE thresholds on real panels before runtime forecast engine. |
| 5 | **Should E-06 proceed?** | **ITERATE** — continue internal forecast research (registry + quality wired; rolling validation PASS). **Do not** start decision engine, recommendation engine, LLM, or user-facing forecast API (PI11 stop rule). |

---

## 2. Recommendation

### **ITERATE E-06** — **COMPLETE PI11 baselines** — **BLOCKED** E-06 production / decision / LLM

| Option | Verdict |
|--------|---------|
| **PROCEED (E-06 runtime)** | **Not selected** — accuracy gate not met on real data; linear fixture fit is misleading |
| **ITERATE (E-06 research)** | **Selected** — retrain baselines on `@5433`; load NCDEX bhav; compare fixture vs integration MAPE; tighten rolling validation on 60/90d |
| **BLOCK (all forecast work)** | **Not selected** — baselines, quality service, and registry are operational |

### Fixture caveat (required for E-06 planning)

The **linear regression 0 MAE / 0 MAPE** result on the PI10 **fixture** panel is **not** evidence of production-grade forecasting. The panel is small (**120** rows, **3** numeric features + spot), deterministic, and approximately linear in spot vs 30d modal target. **E-06 must ITERATE on `@5433` and live-corpus evaluation** before any product forecast path.

---

## 3. Track Verdict (disk @ merge)

| Track | Status | Tests | Evidence |
|-------|--------|-------|----------|
| **A Baselines** | **COMPLETE** | **12** | [FORECAST_BASELINE_REPORT](./FORECAST_BASELINE_REPORT.md); `data/forecast_models/baseline_metrics.json` |
| **B Rolling validation** | **COMPLETE** | **14** | [TIME_SERIES_VALIDATION_REPORT](./TIME_SERIES_VALIDATION_REPORT.md) |
| **C Feature importance** | **COMPLETE** | **10** | [FEATURE_IMPORTANCE_REPORT](./FEATURE_IMPORTANCE_REPORT.md) |
| **D Quality service** | **COMPLETE** | **8** | [FORECAST_QUALITY_REPORT](./FORECAST_QUALITY_REPORT.md); migration `0015` |
| **E Model registry** | **COMPLETE** | **8** | [MODEL_REGISTRY_REPORT](./MODEL_REGISTRY_REPORT.md); migration `0016` |
| **F Program status** | **COMPLETE** | — | [PI11_PROGRAM_STATUS.md](../implementation/PI11_PROGRAM_STATUS.md) |
| **Synthesis handoff** | **COMPLETE** | **7** | `BaselineHandoffService` → registry + quality from Track A JSON |

**PI11 new unit tests (Tracks A–E + handoff):** **59** (12 + 14 + 10 + 8 + 8 + 7).

---

## 4. Baseline metrics @ 30d (fixture rolling OOS)

| Model | MAE (INR) | RMSE (INR) | MAPE (%) | OOS n |
|-------|-----------|------------|----------|-------|
| naive_persistence | 450.00 | 450.00 | 5.7812 | 60 |
| linear_regression | **0.00** ⚠️ fixture | **0.00** | **0.00** | 60 |
| random_forest | **164.30** | **185.68** | **2.0981** | 60 |

**Wired @ merge:** `BaselineHandoffService.sync_from_metrics_json()` registers all three models in `forecast_model_registry` and persists KPIs to `forecast_quality_metric` (`assessment_source=baseline_rolling_oos`).

---

## 5. Validation Snapshot

| Check | Status |
|-------|--------|
| `pytest` (no `DATABASE_URL`) | **278 passed**, 66 skipped, 0 failed |
| `pytest` + `DATABASE_URL` @ 5433 | **339 passed**, 5 skipped, 0 failed |
| `ruff check` | **Pass** |
| `mypy` | **Pass** |
| `alembic upgrade head` @ 5433 | **Pass** — `0016_forecast_model_registry` |
| Rolling validation leakage tests | **PASS** (Track B) |
| Fixture baseline train reproducibility | **PASS** (`train_forecast_baselines.py --fixture`) |
| Forecast dataset reproducibility (`--fixture`) | **PASS** — 120/90/60 rows (inherited PI10) |
| E-06 decision / LLM / user API | **NOT STARTED** (stop rule) |

---

## 6. Program Risks (Top 3)

1. **Fixture ≠ live corpus** — Baseline MAPE/RMSE are not transferable until `@5433` retrain and SR-01 live OGD audit.
2. **Linear 0-error overfitting narrative** — Must not drive E-06 PROCEED; use RF + naive spread as honest fixture band.
3. **Futures feature degeneracy** — Importance ranks Futures high on fixture stubs; `futures_observation` empty @ 5433 until bhav ingest.

---

## 7. Deliverable Checklist (PI11)

| # | Deliverable | Status |
|---|-------------|--------|
| 1 | FORECAST_BASELINE_REPORT + baselines @ 30d | **COMPLETE** |
| 2 | TIME_SERIES_VALIDATION_REPORT + rolling spec | **COMPLETE** |
| 3 | FEATURE_IMPORTANCE_REPORT | **COMPLETE** |
| 4 | FORECAST_QUALITY_REPORT + `ForecastQualityService` | **COMPLETE** |
| 5 | MODEL_REGISTRY_REPORT + `ForecastModelRegistry` | **COMPLETE** |
| 6 | PI11_PROGRAM_STATUS.md | **COMPLETE** |
| 7 | PI11_EXECUTIVE_SUMMARY.md | **COMPLETE** |
| 8 | Track A → D/E metrics handoff | **COMPLETE** |

**Follow-up:** Retrain baselines on `@5433` → set E-06 accuracy thresholds → NCDEX bhav ingest → founder DS-001 OPTION B before production MI.

---

*End of PI11 executive summary.*
