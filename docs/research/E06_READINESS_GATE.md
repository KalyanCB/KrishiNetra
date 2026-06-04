# E-06 Readiness Gate — PI12 Track E (KDO)

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI12 Track E — forecast accuracy readiness gate (research only) |
| **Epic** | E-06 — Forecast Engine (accuracy path; not decision/LLM/runtime) |
| **Workspace** | `c64fe65` |
| **Scope** | Cotton TY-01 baselines @5433; minimum MAPE/RMSE/Coverage; E-06 **PROCEED / ITERATE / BLOCK** |
| **Out of scope** | E-06 decision engine, recommendation engine, LLM agents, user-facing forecast API (PI11+ stop rule) |
| **Baseline docs** | [REAL_FORECAST_BASELINE_REPORT.md](../reviews/REAL_FORECAST_BASELINE_REPORT.md), [REAL_DATASET_AUDIT.md](../reviews/REAL_DATASET_AUDIT.md), [REAL_DATASET_EXPANSION_REPORT.md](../reviews/REAL_DATASET_EXPANSION_REPORT.md), [LEAKAGE_AUDIT_REPORT.md](../reviews/LEAKAGE_AUDIT_REPORT.md), [FORECAST_RESEARCH_DESIGN.md](./FORECAST_RESEARCH_DESIGN.md), TDS-000, TDS-011, TDS-007 |

---

## 1. Executive summary

PI12 closes the **real-corpus baseline loop** on `@5433`: **1,069** supervised rows @30d, temporal embargo **`LEAKAGE_NO`**, and sklearn baselines retrained on JSONL. **Accuracy gates are not evaluable:** every export row has `target_price_level ≡ spot_price_level` (max \|Δ\| = **0 INR**), so rolling OOS MAE/RMSE/MAPE are **0** for naive, linear, and RF; **`beats_naive` = NO** (tied zeros). This is **not** PI11 fixture affine separability — it is **degenerate forward-modal stickiness** on the current basket series (flat fixture-scale modal ladder), not label leakage.

| Question | Gate answer |
|----------|-------------|
| **Is the evaluation panel valid?** | **No** — zero target–spot spread; model ranking **inconclusive** |
| **Is leakage blocking E-06?** | **No** — Track D **`LEAKAGE_NO`** on rolling folds |
| **Can E-06 forecast engine PROCEED?** | **No** — Tier-0 prerequisites failed |
| **E-06 verdict (this gate)** | **ITERATE** — fix targets/features, re-run baselines, then re-gate |
| **E-06 decision / LLM / user API** | **BLOCKED** (unchanged stop rule) |

### PI12 evidence snapshot (@5433, 30d TY-01)

| Check | PI12 result | Gate |
|-------|-------------|------|
| Samples | **1069** | Tier-0 volume **PASS** (≥500) |
| Temporal leakage | **`LEAKAGE_NO`** | Tier-0 **PASS** |
| Non-zero OOS error spread (σ or IQR of \|ŷ−y\| > 0) | **0** on all models | Tier-0 **FAIL** |
| Beat naive on RMSE | **NO** (0 vs 0) | Tier-1 comparative **FAIL** |
| Forward target ≠ spot @ T | **NO** (max \|Δ\|=0) | Tier-0 **FAIL** |
| `target_log_return` informative | **0.0** all rows | Tier-0 **FAIL** |
| Signal features | **0** (no `signal_snapshot`) | Tier-0 feature **FAIL** |

---

## 2. Minimum acceptable forecast KPIs (cotton Phase 1)

Values below are **E-06 research promotion thresholds** for internal forecast-engine start. They are derived from TDS-000 **PROPOSED** Phase-1 targets and TDS-011 interval reliability; they are **not** founder-approved product promotion gates (DVA >3% remains primary per FD-009).

### 2.1 Source definitions (TDS-000 / TDS-011)

| KPI | Formula / unit | TDS-000 Phase-1 target (PROPOSED) | TDS-011 / notes |
|-----|----------------|-----------------------------------|-----------------|
| **RMSE** | INR/qtl; \(\sqrt{\frac{1}{n}\sum(\hat{y}-y)^2}\) | RMSE₃₀ ≤ **8%** of spot; RMSE₆₀ ≤ **10%**; RMSE₉₀ ≤ **12%** | Monitor only; alert if RMSE₃₀ degrades >20% vs 90d baseline (§2.1) |
| **MAPE** | %; excludes \|y\| ≈ 0 | MAPE₃₀ ≤ **7%**; MAPE₆₀ ≤ **9%**; MAPE₉₀ ≤ **11%** | Supplementary to RMSE (§2.2) |
| **Coverage** | Fraction of \(y \in [\hat{y}^{low}, \hat{y}^{high}]\) | — | **80%** nominal interval should cover **~80%** of realizations (§5.1 interval reliability) |

**Illustrative INR bands @ median spot ≈ 9,665 INR/qtl (PI12 export):**

| Horizon | RMSE cap (% of spot) | ≈ INR/qtl cap | MAPE cap |
|---------|----------------------|---------------|----------|
| **30d** | 8% | **≤ 773** | **≤ 7%** |
| **60d** | 10% | **≤ 967** | **≤ 9%** |
| **90d** | 12% | **≤ 1,160** | **≤ 11%** |

**Coverage acceptance (E-06 gate):** For an **80%** prediction interval, rolling OOS **coverage ∈ [0.72, 0.88]** on ≥500 held-out rows per horizon (TDS-011 §5.1 target 0.80 with ±8pp calibration tolerance until live calibration version exists). Bands are **not** scored @ PI12 (baselines are point-only).

**Status:** TDS-000 forecast targets remain **PROPOSED — needs ops/founder sign-off** (TDS-000 §10). This gate **adopts them as E-06 engineering bars** until superseded.

### 2.2 Comparative bar (naive persistence)

| Rule | Definition | Rationale |
|------|------------|-----------|
| **Beat naive (RMSE)** | Best candidate RMSE **strictly <** `naive_persistence` RMSE on same rolling folds | TY-01 naive = spot @ T ([`baselines.py`](../../forecasting/models/baselines.py)); must show learnable horizon structure |
| **Beat naive (MAE)** | Recommended; not sole gate if RMSE passes | Aligns with TDS-000 MAE monitoring |

**PI12 @5433:** naive RMSE = **0.00** → comparative gate **not satisfiable** until Tier-0 target validity passes.

### 2.3 Directional accuracy (informative only)

TDS-000 **PROPOSED:** DA₃₀ ≥ **58%**, DA₆₀ ≥ **55%**, DA₉₀ ≥ **52%**. **Not required** for this E-06 research gate (feeds TDS-011 confidence tuning later).

---

## 3. Tier-0 prerequisites (evaluation validity)

**All must PASS before Tier-1 KPI numbers are interpreted.** Failure here forces **ITERATE** regardless of nominal MAPE/RMSE.

| ID | Prerequisite | Minimum | PI12 @5433 | Status |
|----|--------------|---------|------------|--------|
| **P0-1** | Supervised sample count @30d | ≥ **500** rows, rolling OOS n ≥ **400** | 1069 / 1000 OOS | **PASS** |
| **P0-2** | Temporal label embargo | Track B + rolling train≺test | **`LEAKAGE_NO`** | **PASS** |
| **P0-3** | Forward target differs from spot @ T | median \|y − p₀\| ≥ **50 INR** OR median \|r_h\| ≥ **0.5%** | max \|Δ\| = **0**; all `target_log_return` = **0** | **FAIL** |
| **P0-4** | Non-zero OOS error spread | std(\|ŷ−y\|) ≥ **10 INR** OR IQR ≥ **25 INR** on pooled OOS | **0** all models | **FAIL** |
| **P0-5** | Target construct | TY-01: basket modal @ **T+h** ([FORECAST_RESEARCH_DESIGN](./FORECAST_RESEARCH_DESIGN.md) §2.1) **or** TY-04 log-return with consistent level publish | Code path correct; **series degenerate** (flat modal) | **FAIL** (data) |
| **P0-6** | Feature depth | ≥ **3** numeric signal features @ T beyond spot (PI9 snapshot or TDS-007 §5.2) | **1** feature (spot only) | **FAIL** |

**Root cause (P0-3..P0-5):** Builder resolves `target_price_level = modals[T+h]` correctly ([`builder.py`](../../forecasting/datasets/builder.py)); the **basket modal series is flat** across calendar time on the current `@5433` export (fixture backfill ladder), so ∀T: modal(T+h) = modal(T). **Remediation:** live OGD price variation, validation-pipeline price dispersion, and/or primary evaluation on **TY-04** `target_log_return` when \|r_h\| > ε; add export QA asserting P0-3 before `train_forecast_baselines.py --real`.

---

## 4. Tier-1 accuracy gates (after P0 PASS)

Measured on **rolling expanding OOS** ([`forecasting/backtest/rolling.py`](../../forecasting/backtest/rolling.py): min train 60, test 20, step 20 @ PI12), **primary horizon 30d**, cotton basket modal, `@5433` or successor corpus.

| ID | Metric | 30d minimum (E-06 PROCEED) | 60d / 90d |
|----|--------|----------------------------|-----------|
| **G1** | RMSE | ≤ **773 INR/qtl** (8% × spot) | ≤ 967 / ≤ 1,160 INR (10% / 12%) |
| **G2** | MAPE | ≤ **7%** | ≤ 9% / ≤ 11% |
| **G3** | Coverage (80% band) | **0.72 – 0.88** | Same |
| **G4** | Beat naive RMSE | **YES** (strict inequality) | Same |

**Best model @ PI12:** none — **G1–G4 not evaluated** (Tier-0 failed).

**Fixture reference (PI11, not sufficient for PROCEED):** naive RMSE **450** INR; RF RMSE **185.7** INR; linear **0** INR is affine artifact ([LEAKAGE_AUDIT_REPORT.md](../reviews/LEAKAGE_AUDIT_REPORT.md)) — use RF band for iterate planning only.

---

## 5. PI12 synthesis vs PI11

| Dimension | PI11 (fixture) | PI12 (@5433 real) | Implication |
|-----------|----------------|-------------------|-------------|
| 30d rows | 120 | **1069** | Volume gate cleared |
| Linear MAE | **0** (affine law) | **0** (flat modal) | Different mechanisms; **both block PROCEED** |
| Naive RMSE | **450** INR | **0** INR | Real panel **less informative** than fixture until P0-3 fixed |
| Leakage | N/A (fixture physics) | **`LEAKAGE_NO`** | Methodology trusted; **labels untrusted** |
| `beats_naive` | RF **YES** | **NO** (tied) | No model skill demonstrable on real export |

---

## 6. E-06 decision matrix

| Path | Verdict @ PI12 | Condition |
|------|----------------|-----------|
| **E-06 forecast engine PROCEED** (accuracy-gated implementation) | **BLOCKED** | Tier-0 **FAIL**; Tier-1 not measurable |
| **E-06 forecast research ITERATE** | **SELECTED** | Corpus + leakage OK; fix P0-3..P0-6, retrain, re-gate |
| **E-06 decision / recommendation / LLM / user API** | **BLOCKED** | PI11 stop rule (unchanged) |
| **E-05 production MI publish** | **BLOCKED** | [FORECAST_READINESS_ASSESSMENT.md](./FORECAST_READINESS_ASSESSMENT.md) — Futures / strict snapshot |

---

## 7. Overall gate verdict

| Gate | Result |
|------|--------|
| **Tier-0 (evaluation validity)** | **NOT MET** (P0-3, P0-4, P0-5, P0-6) |
| **Tier-1 (TDS-000 / TDS-011 KPIs)** | **NOT EVALUATED** |
| **Leakage** | **PASS** (`LEAKAGE_NO`) |
| **Corpus scale** | **PASS** (1069 @30d) |
| **E-06 accuracy-gated PROCEED** | **BLOCKED** |
| **E-06 program verdict** | **ITERATE** |

### Verdict: **ITERATE**

**Rationale:** PI12 proves the **pipeline** (dataset export, rolling OOS, registry artifacts, leakage controls) on a **real** `@5433` panel at production-scale row counts, but **fails mandatory readiness requirements**: no non-zero OOS error spread, no beat-naive signal, and no informative forward targets (price level or log-return). Promoting E-06 forecast runtime would bake in a **tautological** label (predict spot at T, realize spot at T when modal is flat). **PROCEED** remains blocked until Tier-0 passes and at least one baseline **beats naive on RMSE** with G1–G2 within TDS-000 PROPOSED bounds.

**Not BLOCK (whole track):** Remediation is scoped and sequenced — no architectural reversal; inherit PI11 baselines, `@5433` corpus, and `LEAKAGE_NO` methodology.

### Top remediation actions (ordered)

| # | Action | Closes |
|---|--------|--------|
| **1** | Export QA: assert median \|target − spot\| ≥ 50 INR or median \|target_log_return\| ≥ 0.5% before `--real` train | P0-3, P0-4 |
| **2** | SR-01 live OGD belt backfill + validation (`VALIDATED` rows); remove flat fixture-only modal ladder | P0-3, P0-5, P0-6 |
| **3** | Backfill `signal_snapshot` @ T; re-export with ≥3 signal numerics | P0-6 |
| **4** | Re-run `train_forecast_baselines.py --real --write-report`; require `beats_naive` **YES** on RMSE | G4 |
| **5** | Score 80% bands + `compute_interval_coverage` (TDS-011 §5.1) | G3 |
| **6** | Re-issue this gate; only then consider **PROCEED** for E-06 engine implementation | Full gate |

---

## 8. Traceability

| Section | Sources |
|---------|---------|
| §1 PI12 state | User PI12 payload; REAL_FORECAST_BASELINE_REPORT; LEAKAGE_AUDIT_REPORT |
| §2 KPI thresholds | TDS-000 §2.1–2.2, §2.5; TDS-011 §5.1; `metrics.py` |
| §3 Targets | FORECAST_RESEARCH_DESIGN §2; `builder.py`; REAL_DATASET_AUDIT §5 |
| §4–5 Baselines | FORECAST_BASELINE_REPORT (PI11); REAL_FORECAST_BASELINE_REPORT |
| §6–7 Verdict | PI11_EXECUTIVE_SUMMARY; FORECAST_READINESS_ASSESSMENT; PI11 stop rule |

---

*End of E-06 Readiness Gate — PI12 Track E.*
