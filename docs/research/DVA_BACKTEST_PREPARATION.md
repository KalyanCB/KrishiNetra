# DVA Backtest Preparation — Cotton Phase 1

**Date:** 2026-06-04  
**PI:** PI5 Track F (KDO — research only)  
**Status:** Complete — **no implementation**, **no new TDS requirements**  
**Sources:** [DVA_PROOF_STRATEGY.md](./DVA_PROOF_STRATEGY.md), [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md), [FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md), [HISTORICAL_BOOTSTRAP_FEASIBILITY.md](./HISTORICAL_BOOTSTRAP_FEASIBILITY.md), TDS-000 §3, TDS-006 §3–§5, TDS-007 §8, TDS-008 §10, TDS-011 §8–§9  
**Related:** FD-003, FD-009, FD-020, REQ-071, REQ-082, REQ-103, DS-001, E-01 (schema), E-03 (ingest), E-04 (agents), E-06 (forecast), E-07 (decision)

---

## 1. What This Document Defines

| Question | Answer in this doc |
|----------|-------------------|
| Minimum historical period for cotton DVA? | **12 calendar months** evaluation window; **36 calendar months** total data span for promotion-grade backtest |
| Required observations? | Price, arrival, weather (+ licensed futures, policy for production track) |
| Required signal history? | Daily `SignalSnapshot` + per-agent `StructuredSignal` for the evaluation window |
| Required forecast history? | Daily pinned `ForecastVersion` rows linked to snapshots |
| Data volume estimates? | Row counts and storage order-of-magnitude for cotton national belt |
| Blockers to running DVA today? | Ranked gaps vs current program state (schema ready; data and pipeline not) |

**Out of scope:** Calibration batch code, dashboard, ingest job implementation, new REQ/TDS amendments.

---

## 2. Minimum Historical Period

### 2.1 Evaluation window (promotion gate)

| Parameter | Value | Authority |
|-----------|-------|-----------|
| **DVA backtest window** | **12 calendar months** | TDS-000 §3.1, TDS-011 §9.1, DVA_PROOF_STRATEGY §5 |
| Simulation step | 1 business day (daily cadence, REQ-140) | TDS-007 §8.1 |
| Monthly bucketing | Calendar months (not rolling 30-day) | TDS-000 KPI-A04 |
| Realized horizons | 30 / 60 / 90 days per registry | TDS-006 §3.3, TDS-008 §10 |

The **12-month window is the minimum period over which aggregate DVA and Positive DVA % are measured** for promotion (DVA > 3%; > 70% positive months).

### 2.2 Total data span (inputs before evaluation)

Promotion-grade backtest requires **more history than the 12-month evaluation window** so features, walk-forward training, and leakage guards have context at the first `as_of_date` in the window.

| Layer | Minimum span | Role | Authority |
|-------|--------------|------|-----------|
| Mandi **price** + **arrival** | **24 months** | Rolling z-scores, seasonal arrival norms, regime diversity | HISTORICAL_BOOTSTRAP_FEASIBILITY §2; TDS-007 §8.2 train window |
| **Weather** regional daily | **36 months** | Seasonal rainfall/drought/harvest-window features | Bootstrap plan §3.5; WEATHER_SIGNAL_FRAMEWORK |
| **Licensed futures** EOD | **12 months** aligned to evaluation window (24+ preferred for curve z-scores) | Hold-to-curve baseline, Futures agent, G6 | FUTURES_DEPENDENCY_ANALYSIS §4; DS-001 |
| Policy / MSP / CCI | Registry + event history spanning evaluation window | MSP/CCI floor regime | TDS-004 §4.3 |
| Global (USDA/ICAC) | Monthly releases; hold-forward acceptable | Global agent features | SIGNAL_ENGINE_V1 §7 |

**Recommended total calendar span for production Track B (licensed):**

```text
┌──────────────────────────────────────────────────────────────┐
│ Months 1–24 (train / feature context) │ Months 25–36 (12m     │
│ Price + arrival + weather context     │ promotion backtest)   │
└──────────────────────────────────────────────────────────────┘
         ↑ 36 mo weather backfill              ↑ DVA evaluation window
```

| Track | Minimum total span | Minimum evaluation window | Production promotion? |
|-------|-------------------|---------------------------|----------------------|
| **A — Exploratory** (spot + weather + policy) | 24 mo price, 36 mo weather | 12 mo (curve leg omitted) | **No** — cannot satisfy G3/G4/G6 |
| **B — Licensed** (Agmarknet + IMD + policy + REQ-071 KAPAS) | **36 mo** (24 context + 12 holdout) | **12 mo** | **Yes** — only track for production proof |

**Geographic minimum:** ≥ **30 primary mandi markets** across multiple states (Gujarat, Maharashtra, Karnataka, Telangana, etc.). Telangana-only (~15–25 mandis) is **insufficient** for regime segmentation (TDS-007 §8.3; HISTORICAL_BOOTSTRAP_FEASIBILITY §2.1).

---

## 3. Required Observations

Observations persist per TDS-006 §3.6–3.7 (E-01-S04). Weather is ingested as regional daily facts feeding the Weather agent; policy/global may use staging tables or agent `signal_components` rather than dedicated observation entities.

### 3.1 Price (`PriceObservation`)

| Field / rule | Requirement |
|--------------|-------------|
| **Source** | Agmarknet primary (REQ-031, REQ-070); eNAM gap-fill only with dedupe |
| **Coverage** | ≥ 30 primary basket markets; national cotton belt |
| **Types** | Modal (primary), min/max where available |
| **Span** | 24 months minimum before evaluation start; 7-day rolling features need contiguous daily rows per market |
| **Schema keys** | `market_id`, `commodity_id`, `price_type`, `value`, `as_of_date`, `source`, `validation_status` |
| **DVA use** | Spot \(p_0\) at decision date T; realized \(p_{T+h}\) for net value paths |

### 3.2 Arrival (`ArrivalObservation`)

| Field / rule | Requirement |
|--------------|-------------|
| **Source** | Agmarknet |
| **Coverage** | Same primary basket as price (~40% of price markets reporting is typical) |
| **Span** | 24 months minimum; sparse gaps acceptable with confidence penalty |
| **Seasonality** | Oct–Mar peak drives Market agent `arrival_zscore` (SIGNAL_ENGINE_V1 §3.2) |
| **DVA use** | Market signal → MI → Decision; supply-pressure regime segmentation |

### 3.3 Weather (regional daily facts)

| Field / rule | Requirement |
|--------------|-------------|
| **Source tier** | IMD API primary; NASA POWER / ERA5 class for historical backfill |
| **Coverage** | Regional rollups for cotton belts keyed by `commodity_id` + `as_of_date` |
| **Span** | **36 months** minimum |
| **Components** | Rainfall anomaly 7d/30d, drought index, harvest-window score, storage humidity risk, acreage proxy (SIGNAL_ENGINE_V1 §4.2) |
| **Persistence** | Staging or feature-store inputs at E-03 design time (not `PriceObservation`) |
| **DVA use** | Weather agent (optional but recommended); regime and seasonal validation slices |

### 3.4 Licensed futures (`FuturesObservation` — production track only)

| Field / rule | Requirement |
|--------------|-------------|
| **Source** | Licensed commercial feed (REQ-071, DS-001); **not** public NCDEX bhav scrape |
| **Contract** | NCDEX KAPAS near/far months per registry |
| **Span** | Full 12-month evaluation window at **≥ 99% trading days** (Gate G6) |
| **Fields** | Near/far prices, OI, volume; basis vs concurrent Agmarknet spot |
| **DVA use** | \(V_{\text{curve}} = (p_{futures,h} - p_0) \cdot q - Carry_{curve}(h)\) (TDS-008 §10.2, FD-003) |

### 3.5 Policy and quality (supporting)

| Input | Requirement |
|-------|-------------|
| MSP / CCI / export policy | Registry `decision_rules` + PIB/CCI events for evaluation window |
| `DataQualitySnapshot` | Per `as_of_date`: `agmarknet_lag_hours`, `futures_feed_ok`, `signals_missing[]` (TDS-006 §3.17) |
| Global fundamentals | USDA/ICAC monthly for Global agent (optional with confidence penalty) |

### 3.6 Observation checklist for backtest start

| Observation class | Exploratory (Track A) | Production (Track B) |
|-------------------|----------------------|----------------------|
| Price (Agmarknet) | **Required** | **Required** |
| Arrival (Agmarknet) | **Required** | **Required** |
| Weather regional daily | **Required** (36 mo) | **Required** (36 mo) |
| Licensed futures EOD | Deferred | **Required** (G6) |
| Policy / MSP events | Recommended | **Required** |
| DataQualitySnapshot | From first simulated refresh day | **Required** daily |

---

## 4. Required Signal History

Per TDS-006 §3.8–3.9 and SIGNAL_ENGINE_V1 §8. Signals may be **persisted** or **regenerated from observations** at replay time (TDS-007 §8.7); promotion proof requires bit-identical replay (REQ-103, Gate G2).

### 4.1 StructuredSignal (per agent, per day)

| Agent | Required for production DVA | Cotton registry weight |
|-------|----------------------------|------------------------|
| **Market** | **Yes** (G6) | 0.22 |
| **Futures** | **Yes** (G6) | 0.25 |
| Weather | Optional (penalty) | 0.13 |
| Policy | Optional (penalty; MSP/CCI rules still work from registry + spot) | 0.15 |
| Global | Optional (penalty) | 0.10 |
| Demand | Out of scope Phase 1 | — |

**Contract fields (E-01-S05):** `agent_type`, `commodity_id`, `as_of_date`, `value`, `direction`, `magnitude`, `confidence`, `signal_components`, `source_observation_refs[]`, `registry_id`, `agent_version`.

**Gate G6:** Futures **and** Market agents present on **≥ 99%** of backtest days (TDS-007 §9, FD-030).

### 4.2 SignalSnapshot (daily bundle)

| Attribute | Requirement |
|-----------|-------------|
| **Cardinality** | 1 per (`commodity_id`, `as_of_date`, `registry_id`) in evaluation window |
| **Count (12 mo daily)** | ~**250–260** snapshots (trading/business days) to ~**365** if calendar-daily grid |
| **Contents** | `signal_ids[]` for active agents, `snapshot_hash`, `data_quality_snapshot_id` |
| **Retention** | Indefinite (replay critical, TDS-006 §3.9) |
| **Leakage rule** | `as_of_timestamp` and observation refs use data ≤ T only (TDS-007 §8.6) |

### 4.3 Signal history volume (12-month evaluation window)

| Table | Formula | Estimate |
|-------|---------|----------|
| `structured_signal` | agents × days | **~1,500–2,200** rows (6 agents × ~250–365 days) |
| `signal_snapshot` | 1 × days | **~250–365** rows |

For **36-month total span** (if backfilling signals): ~**7,500–8,000** structured signals, ~**1,250–1,460** snapshots (forward-generated post E-04, not bulk-loaded in bootstrap).

---

## 5. Required Forecast History

Per TDS-006 §3.11 and TDS-007 §8. Forecast outputs drive Decision NHV; backtest pins a single `model_version` across the evaluation window.

### 5.1 ForecastVersion (per day)

| Field / rule | Requirement |
|--------------|-------------|
| **Cardinality** | 1 published (or replay-flagged) row per `as_of_date` in evaluation window |
| **Horizons** | `horizon_30`, `horizon_60`, `horizon_90` — each with point, lower, upper, direction, confidence |
| **Traceability** | `snapshot_id`, `feature_set_ref`, `model_version`, `registry_id`, `generated_at` |
| **Status** | `complete` for inclusion; failed days break G5 (≥ 97% generation success) |
| **Replay** | Output hash must match recompute on audit sample (Gate G2, REQ-103) |

### 5.2 Feature store linkage

| Store | Requirement |
|-------|-------------|
| `feature_set` / `feature_vector` | Point-in-time assembly at T; full TDS-007 §5.2 vector for Track B includes futures features |
| Walk-forward | Training uses data strictly before holdout; final **12 months never used for model selection** (TDS-007 §8.2) |

### 5.3 Forecast history volume (12-month evaluation window)

| Table | Estimate |
|-------|----------|
| `forecast_version` | **~250–365** rows |
| `feature_set` + vectors | ~250–365 feature sets × ~15–25 features per category |

**Note:** Historical forecasts are typically **recomputed during backtest** from observations + pinned `model_version`, not bulk-imported. Persisted history is required for **replay audit** (G2), not necessarily pre-loaded for all dates before first backtest run.

---

## 6. Data Volume Estimates

National cotton belt assumptions (50–150 markets). Source: HISTORICAL_BOOTSTRAP_FEASIBILITY §3, HISTORICAL_DATA_BOOTSTRAP_PLAN §4.

### 6.1 Observation layer (bootstrap load)

| Stream | Rows / 24 mo | Rows / 36 mo | Storage (order of magnitude) |
|--------|--------------|----------------|--------------------------------|
| `price_observation` | **300k–900k** | **450k–1.35M** | 100 MB–1 GB + indexes |
| `arrival_observation` | **100k–300k** | **150k–450k** | Included above |
| Weather regional daily | 2k–10k (24 mo) | **3k–15k** | < 50 MB |
| Licensed futures EOD | ~500 | ~750 | Negligible |
| Policy / global staging | < 1k | < 2k | Negligible |

**Storage verdict:** Not a blocker at Phase 1 scale (TDS-006 DM2-004; HISTORICAL_BOOTSTRAP_FEASIBILITY §5).

### 6.2 Derived layer (12-month evaluation window only)

| Stream | Row count | Notes |
|--------|-----------|-------|
| `structured_signal` | ~1.5k–2.2k | 6 agents × daily |
| `signal_snapshot` | ~250–365 | 1 per day |
| `forecast_version` | ~250–365 | 1 per day |
| `data_quality_snapshot` | ~250–365 | 1 per refresh |
| Decision simulation outputs | Panel × days × 3 strategies | In-memory or staging tables at calibration run time (not E-01 scope) |

### 6.3 Simulation grid (logical, not persisted pre-run)

For each `as_of_date` T in the 12-month window (TDS-008 §10.1):

| Step | Computes |
|------|----------|
| UserContext panel | Farmer + trader profiles (N + M per T) |
| Three strategies | \(V_{\text{KN}}\), \(V_{\text{sell}}\), \(V_{\text{curve}}\) |
| Aggregation | Monthly \(DVA_m\), then 12m mean; Positive DVA % |

**Daily grid × 3 strategies × panel size** drives compute cost, not PostgreSQL row volume.

---

## 7. Blockers to Running DVA Today

Current program state @ `main` faf3e66: **E-01 schema complete** (migration `0008_decision_stack`); **E-02 cotton seed complete**; **E-03 ingest not started**; **E-04/E-06/E-07 agents and forecast/decision paths design-only**; **DS-001 open**.

### 7.1 Blocker matrix

| ID | Blocker | Impact | Track A (exploratory) | Track B (production) |
|----|---------|--------|----------------------|----------------------|
| **B-01** | **DS-001 / REQ-071** — no licensed NCDEX KAPAS EOD | \(V_{\text{curve}}\) undefined; G6 fail; G3/G4 deferred | Curve leg omitted | **Hard block** |
| **B-02** | **E-03 ingest not operational** — no historical observations in DB | Cannot populate price/arrival/weather/futures | **Hard block** | **Hard block** |
| **B-03** | **E-04 agents not implemented** — no SignalSnapshot generation | Cannot run MI-backed Decision replay | **Hard block** | **Hard block** |
| **B-04** | **E-06 forecast engine not implemented** — no ForecastVersion | NHV and hold/sell paths incomplete | **Hard block** | **Hard block** |
| **B-05** | **E-07 decision backtest runner not implemented** — no three-strategy simulation | DVA aggregation logic exists in TDS only | **Hard block** | **Hard block** |
| **B-06** | **OGD API key / Agmarknet production onboarding** | Blocks bulk historical price load | Blocks bootstrap | Blocks bootstrap |
| **B-07** | **IMD whitelist** (weather primary) | Backfill via NASA POWER possible; production tier degraded | Partial | Partial |
| **B-08** | **Partition ops** — monthly children not pre-created for backfill span | Bulk load failure risk (H-03) | Ops gap | Ops gap |
| **B-09** | **Calibration / DVA batch job** — not implemented (TDS-011) | No automated DVA report artifact | **Hard block** | **Hard block** |
| **B-10** | **OQ-009 legal gate** | Blocks **Promoted** state, not technical backtest | Defer public claims | Defer public claims |

### 7.2 What works today

| Capability | Status |
|------------|--------|
| PostgreSQL schema for observations, signals, forecasts, decisions | **Ready** (E-01) |
| Cotton registry + market FK graph | **Ready** (E-02) |
| DVA formula, gates, and proof procedure documented | **Ready** (DVA_PROOF_STRATEGY, TDS-000/007/008/011) |
| Exploratory DVA computation | **Not runnable** — missing data + pipeline |
| Production DVA proof | **Not runnable** — B-01 + B-02 through B-05 |

### 7.3 Top 3 blockers (ranked)

| Rank | Blocker | Why first |
|------|---------|-----------|
| **1** | **Licensed futures feed unsettled (DS-001 / REQ-071)** | Without \(p_{futures,h}\), hold-to-curve baseline and Gate G6 cannot be satisfied; production DVA is undefined regardless of spot pipeline progress (FUTURES_DEPENDENCY_ANALYSIS §3, DVA_PROOF_STRATEGY §6). |
| **2** | **No historical observation corpus (E-03 ingest)** | Empty `price_observation` / `arrival_observation` / weather staging — backtest has no \(p_0\), no realized prices, no agent inputs. Schema exists; data does not. |
| **3** | **Downstream deterministic pipeline not built (E-04 → E-06 → E-07 + calibration batch)** | Even with observations loaded, DVA requires daily SignalSnapshot, pinned ForecastVersion, Decision Engine simulation, and three-strategy aggregation — none deployed. |

**Near-term unblock sequence (research-aligned, not new requirements):**

1. E-03 Sprint 0 — Agmarknet + weather backfill (24/36 mo national belt).  
2. Founder DS-001 — licensed KAPAS EOD parallel track.  
3. E-04 agents → E-06 forecast → E-07 decision replay → calibration DVA job.  
4. Track A exploratory bake-off while Track B awaits DS-001; **do not treat Track A pass as promotion** (DVA_PROOF_STRATEGY §6.1).

---

## 8. Pre-Backtest Readiness Checklist

Use before first DVA compute job (logical gate, not a new TDS gate):

| # | Check | Track A | Track B |
|---|-------|---------|---------|
| 1 | ≥ 24 mo national cotton price observations loaded | ☐ | ☐ |
| 2 | ≥ 36 mo weather regional daily available | ☐ | ☐ |
| 3 | ≥ 12 contiguous calendar months selected as evaluation window | ☐ | ☐ |
| 4 | Licensed futures EOD ≥ 99% days in evaluation window | — | ☐ |
| 5 | Daily SignalSnapshot regenerable or persisted for window | ☐ | ☐ |
| 6 | Market + Futures agents ≥ 99% days (G6) | Partial | ☐ |
| 7 | ForecastVersion replay hash 100% on audit sample (G2) | ☐ | ☐ |
| 8 | Leakage audit pass (G1) | ☐ | ☐ |
| 9 | Three-strategy simulation with identical carry model (KPI-A02) | Partial (no curve) | ☐ |
| 10 | Version manifest frozen (`model_version`, `registry_id`, `formula_version`) | ☐ | ☐ |

---

## 9. Assumptions

| ID | Assumption |
|----|------------|
| DVA-BP01 | 12 calendar months is the minimum **evaluation** window; 36 months is the minimum **data span** for promotion-grade walk-forward |
| DVA-BP02 | Signals and forecasts for historical dates may be regenerated at backtest time if replay hash matches stored rows |
| DVA-BP03 | Telangana-only mandi subset is insufficient for regime-diverse DVA |
| DVA-BP04 | Track A results are engineering evidence only until Track B passes |

---

## 10. Traceability

| Topic | Document |
|-------|----------|
| DVA formula, 3%, 70%, 12 mo | TDS-000 §3, TDS-011 §8–9, DVA_PROOF_STRATEGY |
| Three-strategy backtest | TDS-008 §10, FD-020 |
| Observation schema | TDS-006 §3.6–3.7, E-01-S04 |
| Signal / snapshot schema | TDS-006 §3.8–3.9, E-01-S05, SIGNAL_ENGINE_V1 |
| Forecast schema | TDS-006 §3.11, E-01-S06, TDS-007 §8 |
| Futures dependency | FUTURES_DEPENDENCY_ANALYSIS, DS-001 |
| Bootstrap volumes | HISTORICAL_BOOTSTRAP_FEASIBILITY, HISTORICAL_DATA_BOOTSTRAP_PLAN |

---

*End of DVA backtest preparation.*
