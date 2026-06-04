# PI12 Executive Summary — Real Corpus Forecast Validation

**Date:** 2026-06-04  
**Synthesized by:** KDO PI12 final synthesis (merge gate)  
**Baseline (pre-PI12):** `c64fe65` — PI11 forecast model baseline  
**Migration head @ merge:** `0016_forecast_model_registry` (unchanged)  
**Recommendation:** **ITERATE E-06** — real pipeline **COMPLETE**; **BLOCKED** E-06 PROCEED / decision / LLM / user API (stop rule)

---

## 1. Executive Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | **How much real data exists?** | **61,547** validated Agmarknet obs; **8,170** weather; **0** futures / signal snapshots. Forecast funnel: **20,882** modal price rows → **1,100** basket dates → **1069 / 1039 / 1009** supervised rows @ 30/60/90d (**≥1000 @30d met**). |
| 2 | **Can forecasting beat naive baseline?** | **No (inconclusive)** — all models report **0** MAE/RMSE/MAPE on rolling OOS because **`target_price_level ≡ spot_price_level`** on every real row (flat basket modal: **9,665** INR for **1,099** of **1,100** days). **`beats_naive` = NO** (tied zeros). |
| 3 | **Is leakage present?** | **No** — Track D verdict **`LEAKAGE_NO`**: chronological rolling folds, target not in `X`, Track B embargo **PASS**. PI11/PI12 zero-error is **fixture affine law** or **flat modal stickiness**, not label leakage. |
| 4 | **Is E-06 justified?** | **Partially** — corpus scale + methodology justify **continued E-06 research**; Tier-0 validity **FAIL** (P0-3..P0-6). **E-06 forecast engine PROCEED: not justified** until forward targets and features are informative ([E06_READINESS_GATE.md](../research/E06_READINESS_GATE.md)). |
| 5 | **Proceed / Iterate / Block?** | **ITERATE** — fix target/corpus (live OGD variation, export QA, `target_log_return` or non-degenerate TY-01, signal snapshot backfill), retrain, re-gate. **Not PROCEED** (E-06 runtime). **Not full BLOCK** of forecast research. |

---

## 2. Recommendation

### **ITERATE E-06** — **COMPLETE PI12 pipeline proof** — **BLOCKED** E-06 PROCEED / decision / LLM

| Option | Verdict |
|--------|---------|
| **PROCEED (E-06 forecast engine)** | **Not selected** — Tier-0 failed; 0-error panel tautological |
| **ITERATE (E-06 research)** | **Selected** — P0-3..P0-6 remediation; re-run `--real` baselines; require `beats_naive` **YES** |
| **BLOCK (all forecast work)** | **Not selected** — `@5433` export, leakage audit, and volume gates are valuable |

### Real-corpus caveat (required for E-06 planning)

The **0 MAE / 0 RMSE / 0 MAPE** result on the PI12 **real** export is **not** production-grade forecasting. The `@5433` basket modal series is effectively **flat** (two levels; one transition), so TY-01 forward modal at **T+30** equals spot at **T** for all **1,069** training rows. **Do not promote** these metrics. **Remediation:** SR-01 live price variation, export QA before `--real` train, evaluate **TY-04** `target_log_return` when \|r_h\| > ε, backfill signal snapshots.

---

## 3. Track Verdict (disk @ merge)

| Track | Status | Tests | Evidence |
|-------|--------|-------|----------|
| **A Real dataset audit** | **COMPLETE** | — | [REAL_DATASET_AUDIT.md](./REAL_DATASET_AUDIT.md) |
| **B Real expansion** | **COMPLETE** | — | [REAL_DATASET_EXPANSION_REPORT.md](./REAL_DATASET_EXPANSION_REPORT.md) |
| **C Real baselines** | **COMPLETE** (inconclusive metrics) | **~4** | [REAL_FORECAST_BASELINE_REPORT.md](./REAL_FORECAST_BASELINE_REPORT.md) |
| **D Leakage audit** | **COMPLETE** | **5** | [LEAKAGE_AUDIT_REPORT.md](./LEAKAGE_AUDIT_REPORT.md) — **`LEAKAGE_NO`** |
| **E E-06 readiness gate** | **COMPLETE** | — | [E06_READINESS_GATE.md](../research/E06_READINESS_GATE.md) — **ITERATE** |
| **F Program status** | **COMPLETE** | — | [PI12_PROGRAM_STATUS.md](../implementation/PI12_PROGRAM_STATUS.md) |

**PI12 new unit tests:** **~9** (5 leakage + ~4 real-corpus baseline).

---

## 4. Real vs fixture @ 30d

| Metric | PI11 fixture | PI12 real @5433 |
|--------|--------------|-----------------|
| Supervised rows | **120** | **1069** |
| Naive MAE | **450** INR | **0** INR |
| Linear MAE | **0** ⚠️ affine | **0** ⚠️ flat modal |
| RF MAE | **164.3** INR | **0** INR |
| `beats_naive` | RF **YES** | **NO** (tie) |
| Leakage | Fixture physics | **`LEAKAGE_NO`** |
| Informative ranking | RF band usable | **None** until P0-3 fixed |

---

## 5. Validation Snapshot

| Check | Status |
|-------|--------|
| `pytest` (no `DATABASE_URL`) | **287 passed**, 66 skipped, 0 failed |
| `ruff check` | **Pass** |
| `mypy` (`forecasting`, scripts) | **Pass** |
| Fixture dataset rebuild (`--fixture`) | **PASS** — 120/90/60 |
| Real dataset rebuild (`real_` prefix @5433) | **PASS** — 1069/1039/1009 |
| Leakage audit (`test_fixture_leakage_audit.py`) | **PASS** |
| Real baseline train (`--real --write-report`) | **PASS** — report + `real_30d/` |
| E-06 decision / LLM / user API | **NOT STARTED** (stop rule) |

---

## 6. Program Risks (Top 3)

1. **Flat modal ladder @5433** — TY-01 labels are tautological; blocks E-06 PROCEED until OGD/validation dispersion restores forward movement.
2. **0-error misread as success** — PI12 real metrics look “perfect” but are **degenerate**; distinct from PI11 fixture affine artifact.
3. **No signal snapshots on DB** — Real exports are spot-only (**P0-6 FAIL**); Futures still **0** rows.

---

## 7. Deliverable Checklist (PI12)

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

**Follow-up:** Export QA (P0-3) → SR-01 live OGD → snapshot backfill → `--real` retrain with `beats_naive` **YES** → re-issue E06 gate.

---

*End of PI12 executive summary.*
