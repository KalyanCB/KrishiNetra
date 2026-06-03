# Forecast Implementation Research Design

**Track:** D (Forecast Research)  
**Branch (intended):** `feature/forecast-research`  
**Status:** Research complete — **no production model selected**  
**Baseline (frozen, read-only):** TDS-007, TDS-011, TDS-000; founder FD-006, FD-009, FD-012, FD-019, FD-020, FD-030; epics E-03+ / E-06 per TDS-014  
**Purpose:** Define how candidate forecast families will be evaluated before E-06 implementation. This document does **not** select a winning model.

---

## 1. Scope and Constraints

| Constraint | Source | Implication for research |
|------------|--------|---------------------------|
| Deterministic forecasting only | TC-001, FD-006, TDS-007 §6 | All candidates must run with pinned seeds, library versions, and `model_version`; no LLM in forecast path |
| Cotton Phase 1 | FD-001, TDS-007 | Universe, features, and benchmarks scoped to cotton registry |
| Central precompute | FD-012 | One forecast per refresh; research must support batch daily cadence |
| DVA primary, accuracy secondary | FD-009, REQ-083 | Ranking and promotion gates use DVA first; RMSE/MAPE inform only |
| No model winner in Wave 2 / Track D | TDS-007 §6.2, §14 | Parallel candidate evaluation only; founder approval required for published winner |
| Replay integrity | REQ-103, NFR-REP-001, NFR-TRC-001 | Research protocol must include hash replay before any promotion claim |

**Out of scope for this document:** Implementation code, registry schema changes, modification of TDS/founder/ADR artifacts.

---

## 2. Target Variables

Targets are derived from TDS-007 §6.4 and TDS-006 `ForecastVersion` persistence. All targets are evaluated **per** `commodity_id`, `as_of_date`, and registry-effective configuration.

### 2.1 Primary supervised targets (model training / error metrics)

| Target ID | Symbol | Definition | Realization time | Notes |
|-----------|--------|------------|------------------|-------|
| **TY-01** | \(y_{30}\) | Realized **price level** at \(T+30\) calendar days | Strictly after `as_of_date` + 30d | Primary horizon for near-term liquidity (REQ-076) |
| **TY-02** | \(y_{60}\) | Realized price level at \(T+60\) | After T+60d | Medium hold |
| **TY-03** | \(y_{90}\) | Realized price level at \(T+90\) | After T+90d | Seasonal / trader positioning |
| **TY-04** | \(r_h\) | Log return \(\ln(y_h / p_0)\) | Same horizons | Optional training formulation; must convert consistently to price level for ForecastVersion publish (TDS-007 FA-002) |

**Reference price \(p_0\):** Spot at `as_of_date` — latest mandi / basis-adjusted spot per TDS-007 §5.2 (`spot_price_level`).

**Leakage rule:** \(y_h\) uses observations with `observed_at` only after horizon elapses; features at \(T\) use `observed_at <= T` end-of-day (TDS-007 §8.6, REQ-103).

### 2.2 Published outputs (not independent training targets)

These are **derived** from model raw outputs + calibration layer (TDS-007 §6.1, TDS-011 §5):

| Output | Per horizon \(h \in \{30,60,90\}\) | Stored in |
|--------|--------------------------------------|-----------|
| Point forecast | \(\hat{p}_h\) | `horizon_*`.point |
| Confidence bands | \([\hat{p}_h^{low}, \hat{p}_h^{high}]\) | lower / upper (80% interval post-calibration, PROPOSED) |
| Direction | \(dir_h = \text{sign}(\hat{p}_h - p_0)\) | direction (bullish/bearish/neutral) |
| Forecast confidence | \(conf_h \in [0,1]\) | confidence — **distinct** from recommendation confidence (TDS-009 §7) |

### 2.3 Auxiliary evaluation targets (not stored as primary TY-*)

| Target | Use |
|--------|-----|
| Direction correctness | \(\mathbf{1}[\text{sign}(\hat{p}_h - p_0) = \text{sign}(y_h - p_0)]\) — feeds DA KPI (TDS-000 §2.4) |
| Band coverage | Whether \(y_h \in [\hat{p}_h^{low}, \hat{p}_h^{high}]\) — feeds calibration (TDS-011 §5.1) |
| Net hold value contribution | Via Decision Engine simulation — feeds **DVA** (primary gate) |

---

## 3. Forecast Horizons

| Horizon | Days | Primary use (TDS-007 §6.3) | Registry |
|---------|------|----------------------------|----------|
| Near | **30** | Sell/hold, farmer liquidity | `forecast_horizons` must include 30 (REQ-076, E-02) |
| Medium | **60** | Medium hold | Same |
| Long | **90** | Seasonal positioning, trader | Same |

**Cadence alignment:** Daily step backtest (REQ-140 working answer); one ForecastVersion row per (`commodity_id`, `as_of_date`, `model_version`, `registry_id`).

**Horizon-specific feature emphasis (TDS-007 §5.2):**

| Horizon | Emphasized feature groups |
|---------|---------------------------|
| 30d | `spot_return_7d`, `arrival_volume_zscore`, `arrival_trend_14d`, `carry_implied_30` |
| 60d | `spot_return_30d`, `regional_strength_dispersion`, `carry_implied_60` |
| 90d | `regional_strength_dispersion`, seasonal/global, `carry_implied_90` |
| All | Market level, basis, futures curve (`curve_slope`, `curve_level_near`, `basis_spot_futures`) |

---

## 4. Feature Candidates (TDS-007 §5.2 Mapping)

Features are assembled point-in-time from **SignalSnapshot** into **feature_set** / **feature_vector** (TDS-006 §10). Names below map 1:1 to TDS-007 conceptual list.

### 4.1 Market features

| TDS-007 name | Research role | Candidate model affinity |
|--------------|---------------|---------------------------|
| `spot_price_level` | Level anchor / normalization | All |
| `spot_return_7d` | Short momentum | Tabular (LGBM, XGB), Ensemble |
| `spot_return_30d` | Medium momentum | Tabular, Ensemble |
| `arrival_volume_zscore` | Supply pressure | Tabular |
| `arrival_trend_14d` | Short supply trend | Tabular |
| `regional_strength_dispersion` | Cross-mandi structure | Tabular |
| `basis_spot_futures` | Cash–futures linkage | All; critical for DVA vs curve benchmark |

### 4.2 Weather features

| TDS-007 name | Notes |
|--------------|-------|
| `rainfall_deficit_index` | Monsoon regime splits |
| `drought_flag` | Binary regime feature |
| `acreage_yoy_change` | Weather Agent (founder clarification) |
| `production_risk_score` | Composite |

### 4.3 Policy features

| TDS-007 name | Regime validation tie-in |
|--------------|-------------------------|
| `msp_level` | MSP floor proximity regime |
| `spot_msp_ratio` | Floor proximity |
| `cci_procurement_active` | CCI active regime |
| `export_restriction_flag` | Policy shock |

### 4.4 Demand features

| TDS-007 name |
|--------------|
| `mill_demand_index` |
| `export_demand_index` |
| `domestic_consumption_trend` |

### 4.5 Futures features

| TDS-007 name | Benchmark tie-in |
|--------------|------------------|
| `curve_slope` | Hold-to-curve baseline (FD-003) |
| `curve_level_near` | Curve level |
| `open_interest_change` | Positioning |
| `basis_futures_spot` | Curve benchmark consistency |
| `carry_implied_30/60/90` | Horizon-aligned carry |

**Critical dependency:** Futures feed required for benchmark and high-confidence publish (TDS-007 §11, FD-030).

### 4.6 Global features

| TDS-007 name |
|--------------|
| `global_inventory_zscore` |
| `global_demand_index` |

### 4.7 Feature assembly invariants (research must enforce)

| Invariant | Source |
|-----------|--------|
| No leakage | `observed_at <= as_of_date` for all inputs |
| `feature_set_ref` on ForecastVersion | Enables replay without re-deriving silently |
| Registry-driven scaling / inclusion | FD-022, CommodityRegistry |
| DataQuality penalties | `confidence_penalty_factor` from DataQualitySnapshot (TDS-011 §10) |

### 4.8 Minimum signal / agent prerequisites (cotton PROPOSED)

Futures + Market agents required; optional agents reduce confidence if missing (TDS-007 §4). Research runs should tag rows with agent completeness for stratified analysis.

---

## 5. Validation Methodology

Validation follows TDS-007 §8 and E-06 intent (F-06-03 bake-off, F-06-06 replay). **Holdout policy:** final 12 months reserved for **promotion backtest only** — never used for hyperparameter selection or model ranking (TDS-007 §8.2).

### 5.1 Walk-forward validation

| Parameter | PROPOSED value | Source |
|-----------|----------------|--------|
| Train window | Expanding or rolling **≥ 24 months** minimum | TDS-007 §8.2 |
| Validation step | **1 month** forward | TDS-007 §8.2 |
| Test holdout | Final **12 months** — promotion only | TDS-007 §8.2 |
| Step (daily simulation) | **1 business day** | TDS-007 §8.1, REQ-140 |

```mermaid
flowchart LR
  TR[Train up to Tk] --> VA[Validate month Tk+1]
  VA --> TR2[Expand train]
  TR2 --> VA2[Validate Tk+2]
  VA2 --> HOLD[12mo holdout: promotion only]
```

### 5.2 Promotion backtest (12 calendar months)

| Parameter | Value |
|-----------|-------|
| Window | 12 calendar months (approved) |
| Universe | Cotton; all active registry versions in window |
| Strategies | Sell immediately \| Hold to futures curve \| KrishiNetra (TDS-007 §7, FD-020) |
| Primary metric | **DVA > 3%** (approved) |
| Secondary consistency | **Positive DVA months > 70%** (approved) |

**Per-date procedure (research replay of production path):**

1. Load registry effective on `as_of_date`
2. Rebuild or load SignalSnapshot from observations (E-03+ dependency)
3. Assemble Feature Store with leakage guards → `feature_set_ref`
4. Run Model Runner with **pinned** `model_version` per candidate
5. Simulate Decision Engine with representative UserContext panel (farmer + trader)
6. Compute realized net value after carry at horizon using **realized** prices
7. Aggregate DVA vs baselines

### 5.3 Regime validation

Segment results (TDS-007 §8.3); KrishiNetra path must not fail **only** in liquidity-critical regimes:

| Regime | Segmentation |
|--------|--------------|
| MSP floor proximity | spot within ±3% MSP vs not (founder clarification, E-02) |
| CCI active | procurement on vs off |
| High volatility | realized vol > 75th percentile |
| Agmarknet degraded | DataQualitySnapshot penalty active |

Report **DVA per regime** and forecast KPIs (RMSE, DA) per regime.

### 5.4 Seasonality validation

| Check | Method |
|-------|--------|
| Crop year quarter | Compare DA and DVA by quarter |
| Seasonal error | Seasonal MAPE split (especially relevant for Prophet candidate) |
| Band width | Widen bands in monsoon / export-policy windows |

### 5.5 Forecast KPI monitoring (secondary)

From TDS-000 §2 — **not promotion gates**:

| KPI | Horizons | Role in research |
|-----|----------|------------------|
| RMSE | 30 / 60 / 90 | Monitor; alert if >20% vs 90d baseline |
| MAPE | 30 / 60 / 90 | Scale-free comparison |
| MAE | 30 / 60 / 90 | Stakeholder communication |
| Directional accuracy | 30 / 60 / 90 | Informs confidence tuning |

**Explicit acceptance rule (FD-009):** High RMSE + positive DVA → acceptable for candidate to remain in bake-off; low RMSE + negative DVA → reject candidate.

### 5.6 Data leakage prevention

| Check | Enforcement |
|-------|-------------|
| Temporal cutoff | `observed_at <= as_of_date 23:59:59` |
| Feature join | As-of merge only |
| Target | \(y_h\) strictly after T+h |
| Futures | Curve as known at T, not revised history |
| Registry | Version effective at T only |
| Automated | Replay hash mismatch → alarm |

**Manual audit:** Random sample **50 dates**; verify observation timestamps (TDS-007 §8.6).

### 5.7 Forecast replay validation (REQ-103)

| Step | Action |
|------|--------|
| Input | `commodity_id`, `as_of_date`, `model_version`, `registry_id` |
| Reconstruct | SignalSnapshot or observations → Feature Store (`feature_set_ref` or recompute) |
| Run | Model Runner with pinned version |
| Compare | Output hash vs stored ForecastVersion |
| Acceptance | **100% match** on **30-date** audit sample before promotion (TDS-007 §8.7, TDS-000 §6) |

---

## 6. Calibration Methodology (TDS-011)

Calibration is **deterministic** given `calibration_version` — it must not introduce runtime randomness (FD-006, TDS-011 §14).

### 6.1 Objectives

| Objective | Metric | Phase 1 scope |
|-----------|--------|---------------|
| Direction reliability | DA by horizon | Primary for \(conf_h\) |
| Interval reliability | ~80% band coverage | Band low/high |
| Bias correction | Mean error → 0 | Monitor; point \(\hat{p}_h\) unchanged in Phase 1 (PROPOSED) |

### 6.2 Process (weekly batch alignment)

| Step | Description | Determinism |
|------|-------------|-------------|
| 1 | Collect (ForecastVersion, realized \(y_h\)) pairs | Batch |
| 2 | Compute RMSE, MAPE, MAE, DA (TDS-000) | Batch |
| 3 | Bin \((conf, \text{outcome})\) by decile; reliability diagram | Batch |
| 4 | Fit mapping per horizon: Platt or isotonic (Wave 3 implementation detail) | Versioned |
| 5 | Store `calibration_version` on ForecastVersion | Immutable version pin |
| 6 | Apply in Forecast Engine post-processor | \(conf_{calibrated} = clip(f(conf_{raw}, regime, calibration\_version), 0, 1)\) |

**Phase 1 constraint (PROPOSED):** Calibration adjusts **confidence and bands**, not point forecast \(\hat{p}_h\) (TDS-011 §5.3).

### 6.3 Rejection criteria for candidates

| Criterion | Threshold | Source |
|-----------|-----------|--------|
| Calibration error | Mean calibration error ≤ 0.08 target; reject if worsens >15% vs baseline at promotion | TDS-000 §4.1 |
| Reliability | Decile reliability diagram review | TDS-007 §8.5 |

### 6.4 Drift interaction

Forecast drift signals (RMSE spike, DA collapse, PSI > 0.2) trigger warnings or promotion block — no online learning without new `model_version` (TDS-011 §12).

---

## 7. Benchmark Methodology (DVA Gate)

Economic benchmarks tie forecast research to **Decision Value Added** — not standalone forecast leaderboard.

### 7.1 Three strategies (FD-020, TDS-007 §7)

| Strategy | Definition | Role |
|----------|------------|------|
| **Sell immediately** | Liquidate at spot on `as_of_date` | Baseline 1 |
| **Hold to futures curve** | Hold to horizon implied by futures curve net of carry | Baseline 2 (FD-003) |
| **KrishiNetra** | Follow deterministic recommendation from Decision Engine | Strategy under test |

### 7.2 DVA formula (TDS-000 §3.1, TDS-011 §8.1)

\[
DVA_{12m} = \overline{V_{KN}} - \max(\overline{V_{sell}}, \overline{V_{curve}})
\]

Net of carry; 12 calendar months; cotton universe.

\[
PositiveDVA\% = \frac{\#\{months : DVA_m > 0\}}{12}
\]

### 7.3 Unified promotion gate (research must document per candidate)

| Criterion | Threshold | Status |
|-----------|-----------|--------|
| Backtest window | 12 calendar months | **APPROVED** |
| Aggregate DVA | **> 3%** | **APPROVED** |
| Positive DVA months | **> 70%** | **APPROVED** |
| Deterministic replay | 100% match on sample (REQ-103) | **APPROVED** |
| Leakage audit | Pass | TDS-007 G1 |
| Forecast generation success (staging) | ≥ 97% | TDS-007 G5, TDS-000 |
| Futures + Market agents | ≥ 99% days | TDS-007 G6 |
| No LLM in pipeline | Audit pass | TDS-007 G7 |
| Legal review | Complete | **PENDING** (OQ-009) |

**Ranking rule for bake-off (TDS-007 §6.2):** Rank candidates on **DVA-contributing metrics first**, forecast KPIs second.

### 7.4 Pre-production validation gate checklist (G1–G7)

Research deliverable for each candidate family: evidence pack mapping to TDS-007 §9 gates — pass/fail per gate, no aggregate winner declared in Track D.

---

## 8. Candidate Model Comparison (No Winner Selected)

The following compares **LightGBM**, **XGBoost**, **Prophet**, and **Ensemble** for cotton Phase 1 tabular + seasonal forecasting. **No candidate is selected** in this document; E-06 F-06-03 bake-off and founder approval determine the published `model_version`.

### 8.1 Summary matrix

| Dimension | LightGBM | XGBoost | Prophet | Ensemble |
|-----------|----------|---------|---------|----------|
| **Strengths (cotton)** | Fast tabular iteration; native missing values (Agmarknet gaps); strong interactions on basis/arrival | Robust nonlinear interactions; mature ecosystem | Explicit seasonality/holidays; interpretable trend/seasonality | Can blend tabular + seasonal; potentially best of both |
| **Risks** | Overfit without leakage controls | Same overfit/leakage risk | Weak on policy/futures jumps; fewer exogenous regressors by default | Complexity; reproducibility discipline |
| **Data needs** | Rich feature matrix from §4; min ~24mo train | Same as LGBM | Regular daily series per target; regressor columns for policy/futures | All of the above + blend weights versioning |
| **Missing data** | Handles missing features well | Handles missing features well | Gaps require imputation or missing fill rules | Must define deterministic imputation upstream |
| **Seasonality** | Implicit via features | Implicit via features | Explicit seasonal components | Seasonal component + tabular residuals |
| **Horizons 30/60/90** | Multi-output or separate models per h | Same | Separate models or single model with horizon as regressor | Per-component versioning |
| **Training cost** | Low–medium | Low–medium | Medium (per series) | High (multiple fits + blend) |
| **Inference latency** | Low (batch friendly) | Low | Medium | Highest |
| **Determinism / REQ-103** | Seed + pinned `lightgbm` version in `model_version` | Seed + pinned `xgboost` version | `random_seed` where applicable; pinned `prophet`/`cmdstan` versions | **Highest risk:** blend weights, multiple seeds, staging order must be frozen |
| **Replay** | Serialize booster + feature list hash | Same | Serialize stan backend settings + regressor snapshot | Serialize all sub-models + weights + assembly order |
| **DVA alignment** | Strong if futures/market features dominate | Strong | Moderate unless exogenous regressors include curve/policy | Potentially strongest if disciplined |
| **Regime sensitivity** | Good with explicit regime features | Good | May smooth policy shocks | Depends on blend design |

### 8.2 LightGBM

| Aspect | Assessment |
|--------|------------|
| **Pros** | Fast experimentation for F-06-02 runners; handles Agmarknet lag/gaps (FD-030); fits TDS-007 tabular feature store design |
| **Cons** | Hyperparameter search must stay inside walk-forward folds only; risk of overfitting high-dimensional policy/futures spikes |
| **Data needs** | Full §4 feature vector; minimum train window 24 months; futures + market signals for credible curve-relative forecasts |
| **Determinism** | Set `random_state`, `deterministic=True` (version-dependent), disable nondeterministic GPU if used; record `model_version` = `{family}-{lib_version}-{seed}-{train_end_date}` |
| **Replay** | Persist booster binary + exact feature column order and scaling params from registry |

### 8.3 XGBoost

| Aspect | Assessment |
|--------|------------|
| **Pros** | Similar to LightGBM; strong default for heterogeneous tabular signals; well-understood CI pinning |
| **Cons** | Same leakage/overfit discipline required; training slower than LightGBM at scale |
| **Data needs** | Identical feature matrix to LightGBM for fair bake-off |
| **Determinism** | `random_state`, `tree_method` choices documented; avoid GPU nondeterminism in replay audits |
| **Replay** | JSON/binary model + feature manifest hash |

### 8.4 Prophet

| Aspect | Assessment |
|--------|------------|
| **Pros** | Explicit seasonality validation (TDS-007 §8.4); good diagnostic for seasonal MAPE splits |
| **Cons** | Weaker on abrupt policy/export restrictions; default univariate focus may underuse cross-signal features unless added as regressors |
| **Data needs** | Continuous daily target series per commodity/region; regressor sync for `curve_slope`, policy flags, quality penalties |
| **Determinism** | Pin Stan backend version; fixed seeds; document holidays/regressor schema in `model_version` |
| **Replay** | Serialize fitted model + regressor dataframe hash at `as_of_date` |

### 8.5 Ensemble

| Aspect | Assessment |
|--------|------------|
| **Pros** | Can combine Prophet seasonal structure with LGBM/XGB tabular residuals (TDS-007 candidate list) |
| **Cons** | Highest complexity; greatest replay risk if blend or sub-model order not versioned |
| **Data needs** | Superset of single-family requirements; offline weights only (no online learning — TDS-011 §14) |
| **Determinism** | Single `model_version` string must encode: sub-model versions, blend weights, assembly DAG, imputation rules |
| **Replay** | Require integration test: 30-date hash match **per sub-model and combined output** |

### 8.6 Explicit statement

**No winning model is selected in Track D.** All four families remain **candidates** for E-06 offline evaluation (F-06-03). Final `is_published` winner requires founder approval after bake-off (TDS-007 §14, §15).

---

## 9. Dependencies on Upstream Epics (E-03+)

| Epic | Dependency for forecast research |
|------|----------------------------------|
| E-03 | Observations (price, arrival, weather, policy, demand, futures, global) with `as_of_date`, supersede chain |
| E-04 | Six domain agents → SignalSnapshot |
| E-05 | DATA_REFRESH orchestration, daily cadence |
| E-02 | CommodityRegistry: `forecast_horizons` [30,60,90], sources, scaling config |
| E-01 | `forecast_version`, `feature_set`, `feature_vector` tables |
| E-06 | Implementation of this research design (runners, bake-off, publish) |
| E-07+ | Decision simulation for DVA |
| E-10 | Calibration batch, DVA rolling reports, promotion state machine |

**Blocking data risks (from readiness reviews):** Commercial futures feed (REQ-071) not validated in repo — benchmark and `basis_*` features depend on it.

---

## 10. Research Deliverables (E-06 Inputs)

| Deliverable | Description |
|-------------|-------------|
| Candidate scorecard | Per-family pass/fail on G1–G7 + DVA/Positive DVA% |
| Feature coverage report | % non-null per §4 feature by regime |
| Replay audit log | 30-date hash results per `model_version` |
| Calibration pack | Reliability diagrams per horizon per candidate |
| Regime / seasonality appendix | DVA and DA segmented tables |

---

## 11. Open Questions (Track D)

| ID | Question | Blocks |
|----|----------|--------|
| OQ-004 | Material signal movement (stability) | Indirect — decision stability in DVA simulation |
| TDS-007 | Final model selection after offline bake-off | Founder approval of winner |
| TDS-000 | PROPOSED RMSE/MAPE targets | Ops/founder sign-off — not promotion gates |
| OQ-007 | Outcome capture workflow | Live calibration loop (E-10) |
| OQ-009 | Legal gate on promotion | Public promotion claims |
| DS-001 | Futures feed vendor contract | Credible hold-to-curve benchmark |
| — | Train window: expanding vs rolling 24mo | Walk-forward protocol finalization |
| — | Point vs return training target (TY-04) | Must be consistent at publish boundary |

---

## 12. Traceability

| Research section | TDS | REQ | FD |
|------------------|-----|-----|-----|
| Target variables / horizons | TDS-007 §5–6, TDS-006 | REQ-076 | FD-001 |
| Validation / leakage / replay | TDS-007 §8 | REQ-103, REQ-102 | FD-006, FD-027 |
| Calibration | TDS-011 §5 | REQ-081, REQ-084 | FD-021 |
| DVA benchmark | TDS-000 §3, TDS-007 §7–9, TDS-011 §8–9 | REQ-100–102, REQ-083 | FD-003, FD-009, FD-020 |
| Candidates | TDS-007 §6.2 | REQ-056, REQ-063 | FD-006, FD-019 |
| Features | TDS-007 §5 | REQ-103 | FD-022, FD-030 |

---

## Document Control

| Version | Date | Author | Notes |
|---------|------|--------|-------|
| 1.0 | 2026-06-03 | Track D | Initial research design; no model winner |
