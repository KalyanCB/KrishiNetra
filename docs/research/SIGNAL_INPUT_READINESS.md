# Signal Input Readiness — PI5 Track E (E-04 Prerequisites)

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI5 Track E (KDO — research / validation only) |
| **HEAD (validated)** | `faf3e66` @ `main` (PI5 tracks A–G on disk) |
| **Epic** | E-04 — Domain Agents (deterministic); **no signal runtime** in this deliverable |
| **Scope** | Whether **current persisted observations** and registry fields can feed **Market**, **Weather**, and **Policy** agents per [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §3–§5 |
| **Out of scope** | Futures / Global / Demand agents; LangGraph orchestration; `structured_signal` implementation |

---

## 1. Executive Summary

PI5 proves **Agmarknet → observation persistence** (8 cotton rows) and **live weather API access** (spike only), but **observation depth and source coverage are insufficient** for production-grade Market, Weather, or Policy signals. Weather has **no observation store**; Policy lacks **MSP absolute value** and **CCI/PIB event** inputs in registry or DB.

### 1.1 Per-signal readiness

| Signal | Verdict | One-line rationale |
|--------|---------|-------------------|
| **Market** | **PARTIAL** | 8 Agmarknet rows prove FK + mapping; **cannot** compute 30d z-scores, basket coverage, or lag-adjusted confidence |
| **Weather** | **BLOCKED** | Zero weather rows in DB; IMD PRIMARY blocked (WS-01); NASA POWER proven only in spike |
| **Policy** | **PARTIAL** | Modal spot derivable from price rows; **no** `msp_inr_quintal`, CCI, export, or volume observations |

### 1.2 Cotton registry agent roles (context)

From [`cotton.json`](../../backend/app/persistence/seeds/fixtures/cotton.json) @ v1.0.0:

| Role | Agents | E-04 gate |
|------|--------|-----------|
| **Required** | `Market`, `Futures` | Strict MI publish blocked if either missing ([SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §8, TDS-009 §9) |
| **Optional** | `Weather`, `Policy`, `Demand`, `Global` | Omission → MI confidence penalty, not pipeline abort |

**Track E scope:** Validates **input observations** for the three optional/research-critical agents above. **Futures** remains a separate **BLOCKED** track (DS-001, REQ-071) and is an **E-04 orchestration blocker** even when Market inputs improve.

### 1.3 Top gaps for E-04 (priority order)

| ID | Gap | Blocks |
|----|-----|--------|
| **SI-01** | **Futures feed DS-001** unsigned; no `FuturesObservation` table/ingest; `futures_feed_ok` unset | Strict MI + required-agent gate; Market basis-fallback penalty path |
| **SI-02** | **No weather observation persistence** (no E-01 weather DDL) | Weather agent `source_refs[]` lineage (AC-05) |
| **SI-03** | **Market history depth** — 8 rows, 2 dates, 2/4 mandis; no 30d rolling series | `price_trend_zscore`, `arrival_zscore`, `primary_markets_reporting_pct` |
| **SI-04** | **`data_quality_snapshot` not written by ingest** — no `agmarknet_lag_hours` | Market confidence §3.5 |
| **SI-05** | **Policy MSP absolute missing** in `decision_rules` (only `msp_proximity_pct`) | `msp_inr_quintal`, `spot_vs_msp_pct`, MSP_FLOOR regime |
| **SI-06** | **No PIB/CCI/export policy ingest** | `cci_active_procurement`, volume, export flags |
| **SI-07** | **Partition backfill (G7)** — only `*_2026_06` + DEFAULT; multi-month Agmarknet/weather bootstrap needs forward DDL | Historical replay and backtest windows |
| **SI-08** | **Production Agmarknet pipeline** (OGD key G2, cron, dedupe G9) | Daily refresh cycle (REQ-140) |

---

## 2. Validation Method

| Input artifact | Role in this assessment |
|----------------|-------------------------|
| [E03_SPRINT0_AUDIT.md](../reviews/E03_SPRINT0_AUDIT.md) | Schema READY; ingest G1–G11; partition G7 |
| [AGMARKNET_SPIKE_REPORT.md](../reviews/AGMARKNET_SPIKE_REPORT.md) | OGD → observation mapping contract |
| [OBSERVATION_POPULATION_REPORT.md](../reviews/OBSERVATION_POPULATION_REPORT.md) | **8 persisted cotton observations** (ground truth counts) |
| [WEATHER_SPIKE_REPORT.md](../reviews/WEATHER_SPIKE_REPORT.md) | API viability; **no DB weather rows** |
| [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) | Required inputs per agent §3–§5 |
| [COTTON_INTELLIGENCE_MODEL_V1.md](./COTTON_INTELLIGENCE_MODEL_V1.md) | Lifecycle gating (e.g. arrival z Oct–Mar) |
| [`cotton.json`](../../backend/app/persistence/seeds/fixtures/cotton.json) | `required_agents`, `policy_drivers`, `weather_variables` |

**Rule:** “Data available today” means **rows queryable from Postgres** after PI5 Track C proof (or registry fields loaded via `RegistryService`), not spike-only in-memory pulls.

---

## 3. Current Observation Inventory

### 3.1 Persisted (Postgres @ PI5 Track C)

| Table | Cotton / Agmarknet count | Date span | Markets |
|-------|--------------------------|-----------|---------|
| `price_observation` | **7** (`source=agmarknet`) | `2022-03-26`, `2026-06-04` | `mkt_tg_khammam_apmc`, `mkt_tg_warangal` |
| `arrival_observation` | **1** | `2022-03-26` | `mkt_tg_khammam_apmc` |
| **Total** | **8** | 2 distinct `as_of_date` values | **2 / 4** seeded Telangana mandis |

**Not persisted:** weather series, futures EOD, policy events, USDA/ICAC, `data_quality_snapshot` rows from ingest.

### 3.2 Registry fields relevant to signals (no extra observation tables)

| Field | Present @ v1.0.0 | Signal use |
|-------|------------------|------------|
| `price_sources` / `arrival_sources` | Agmarknet (+ eNAM listed, no rows) | Market basket definition |
| `decision_rules.msp_proximity_pct` | `0.03` | Policy / Decision proximity threshold |
| `decision_rules` → `msp_inr_quintal` | **Absent** | Policy `msp_inr_quintal`, `spot_vs_msp_pct` |
| `policy_drivers` | `["MSP","CCI","PIB"]` | Source list only — no automated ingest |
| `weather_variables` | `["rainfall","humidity","acreage"]` | Agent feature names — no climatology seed in DB |

### 3.3 Schema gaps (observation types)

| SIGNAL_ENGINE input type | Migration @ `0008` | Status |
|--------------------------|-------------------|--------|
| `PriceObservation[]` | `price_observation` | **Exists** — sparsely populated |
| `ArrivalObservation[]` | `arrival_observation` | **Exists** — 1 row |
| District rainfall / weather | **No dedicated table** | **Missing** — spike modules only |
| `FuturesObservation[]` | **No dedicated table** | **Missing** — DS-001 (SI-01) |
| Policy events (PIB/CCI) | **No dedicated table** | **Missing** — registry + derived spot only |

TDS-006 documents price/arrival observations; weather agent inputs were planned as observations or prep for `signal_components` ([E03_DATA_INGESTION_READINESS.md](./E03_DATA_INGESTION_READINESS.md) §3.3) — **not implemented in E-01 migrations**.

---

## 4. Market Signal — `agent_type = Market`

**Spec:** [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §3 — modal/min/max prices, arrivals, registry basket, `DataQualitySnapshot`, optional Futures basis fallback.

### 4.1 Data available today

| Input | Available? | Evidence |
|-------|------------|----------|
| Modal/min/max prices | **Partial** | 7 price rows: Khammam min/max/modal @ `2022-03-26`; Warangal modal @ `2026-06-04` |
| Arrival volumes | **Minimal** | 1 arrival @ Khammam `2022-03-26` (425 quintals) |
| Market basket (4 Telangana mandis) | **Registry only** | 4 markets seeded; **2** have any price rows |
| `agmarknet_lag_hours` | **No** | `data_quality_snapshot` not populated by ingest (E-03 G8) |
| Futures basis fallback | **No** | DS-001 / no futures observations (SI-01) |

### 4.2 Gaps vs SIGNAL_ENGINE_V1

| Feature / confidence factor | Requirement | Gap |
|----------------------------|-------------|-----|
| `price_trend_zscore` | 30d rolling modal (primary basket) | **BLOCKED** — max 1 day per market in DB; no contiguous 30d series |
| `arrival_zscore` | Seasonal norm; **Oct–Mar only** (FG-01) | **BLOCKED** — single arrival date (Mar 2022); no seasonal baseline ingested |
| `regional_strength_index` | Cross-market dispersion | **BLOCKED** — need ≥2 markets × multi-day; only 2 markets × 1 day each |
| `primary_markets_reporting_pct` | Daily basket coverage | **BLOCKED** — 50% markets ever reported; not a trading-day series |
| Confidence `λ_lag` | `agmarknet_lag_hours` | **BLOCKED** — no quality snapshot from ingest |
| `penalty_basis_fallback` | Licensed futures + spot | **BLOCKED** — SI-01 |
| Production idempotency | Business-key dedupe | **OPEN** — append-only proof; re-run duplicates rows ([OBSERVATION_POPULATION_REPORT.md](../reviews/OBSERVATION_POPULATION_REPORT.md) §7) |

### 4.3 Minimum additional ingest (Market → **READY**)

| # | Deliverable | Owner |
|---|-------------|-------|
| M-1 | **Production Agmarknet daily load** for 4 Telangana mandis (modal + optional min/max) | E-03 |
| M-2 | **≥30 consecutive trading days** per primary market (or documented basket rollup) | E-03 backfill |
| M-3 | **Arrival channel** with tonnes (zip/portal or OGD extension) for Oct–Mar windows | E-03 G6 |
| M-4 | **`data_quality_snapshot`** row per refresh with `agmarknet_lag_hours`, `registry_id` | E-03 G8 |
| M-5 | **Partition DDL** for backfill months (G7) — e.g. `2022-03`, `2024-*`, `2026-06+` | E-03/DBA |
| M-6 | **90-day mandi audit** (G5) — spelling / reporting coverage | E-02/E-03 |

**Degraded E-04 path:** Emit Market signal with **neutral direction / near-zero magnitude** and very low confidence using sparse rows — **not** spec-compliant for MI narratives; useful only for wiring tests.

### 4.4 E-04 blockers (Market-specific)

| Blocker | Severity |
|---------|----------|
| SI-03 history depth | **Hard** for z-score transforms |
| SI-04 quality snapshot | **Hard** for confidence formula |
| SI-07 partition backfill | **Hard** for historical replay @ `2022-03-26` in named partitions (DEFAULT works for proof only) |
| SI-08 production pipeline | **Hard** for daily `DATA_REFRESH_START` |
| SI-01 futures (basis fallback) | **Soft** for Market alone — degrades confidence when Agmarknet gaps; **hard** for full MI |

**Verdict: PARTIAL** — persistence and mapping **proven**; **not READY** for deterministic daily Market signal per §3.2–3.5.

---

## 5. Weather Signal — `agent_type = Weather`

**Spec:** [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §4 — IMD district rainfall (primary), NASA POWER gap-fill, nowcast, acreage proxy, registry `weather_variables` / climatology.

### 5.1 Data available today

| Input | Available? | Evidence |
|-------|------------|----------|
| District/state rainfall observations | **No** | No weather table; zero persisted rows |
| NASA POWER daily series | **Spike only** | [WEATHER_SPIKE_REPORT.md](../reviews/WEATHER_SPIKE_REPORT.md) — live HTTP 200, 36-mo pull **not loaded to Postgres** |
| IMD district actual/normal/departure | **No** | HTTP 401 API key missing (WS-01) |
| IMD nowcast | **No** | Not probed to DB |
| Acreage proxy | **No** | Non-IMD source; not ingested |
| Climatological norms | **No** | Registry lists variable names only |
| `region.external_refs` IMD `OBJ_ID` | **No** | WS-02 open |

### 5.2 Gaps vs SIGNAL_ENGINE_V1

| Gap ID | Description | Source |
|--------|-------------|--------|
| **WS-01** | IMD API key + IP whitelist | WEATHER_SPIKE §7 |
| **WS-02** | `OBJ_ID` → `region_id` mapping | WEATHER_SPIKE §7 |
| **WS-03** | ~0.5° grid collapses adjacent districts | Rollup + confidence penalty (WQ-01) |
| **WS-04** | NASA POWER lacks departure/category semantics | PRIMARY must stay IMD for anomalies |
| **WS-05** | 36 mo BACKFILL not persisted | One-time POWER pull per belt region |
| **SI-02** | **No weather observation DDL** | E-01 scope gap vs E03 readiness “weather observations” |

### 5.3 Minimum additional ingest (Weather → **READY**)

| # | Deliverable | Owner |
|---|-------------|-------|
| W-1 | **Define and migrate** weather observation store (district × `as_of_date` × metrics) OR documented alternative aligned to TDS-006 | E-01/E-03 |
| W-2 | **Map** Telangana cotton districts to `region_id` (+ IMD `OBJ_ID` in `external_refs`) | E-02/E-03 |
| W-3 | **Daily ingest** — IMD PRIMARY post WS-01; NASA POWER SECONDARY for gap-fill | E-03 Track D |
| W-4 | **Climatology seed** for 7d/30d anomaly baselines | E-03 / registry extension |
| W-5 | **36–60 mo backfill** (WS-05) before Weather backtest | E-03 bootstrap |
| W-6 | **Optional:** acreage proxy source (state ag stats / USDA) | E-03 parallel |

**Sprint 0 dev unblock:** NASA POWER → weather store **without** IMD PRIMARY still yields **PARTIAL** signal (lower confidence, missing departure/category) per strategy V1.

### 5.4 E-04 blockers (Weather-specific)

| Blocker | Severity |
|---------|----------|
| SI-02 no observation persistence | **Hard** — AC-05 `source_refs[]` to E-03 observations |
| WS-01 IMD PRIMARY | **Hard** for production-grade anomaly features |
| WS-05 history | **Hard** for `rainfall_anomaly_30d` and backtest |
| Optional agent | **Soft** for MI publish — Weather omission penalizes MI, does not abort ([cotton.json](../../backend/app/persistence/seeds/fixtures/cotton.json)) |

**Verdict: BLOCKED** on “current observations” — **no weather observations exist**. Spike proves **source access**, not signal input readiness.

---

## 6. Policy Signal — `agent_type = Policy`

**Spec:** [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §5 — MSP, spot vs MSP, CCI procurement, export restrictions; [PROCUREMENT_SIGNAL_MODEL.md](./PROCUREMENT_SIGNAL_MODEL.md).

### 6.1 Data available today

| Input | Available? | Evidence |
|-------|------------|----------|
| Spot modal price (Agmarknet) | **Partial** | Derivable from 7 price rows (modal types); **2 dates**, **2 markets** |
| `msp_inr_quintal` | **No** | Not in `decision_rules` — only `msp_proximity_pct` in seed |
| `spot_vs_msp_pct` | **No** | Requires MSP absolute + spot |
| `cci_active_procurement` | **No** | No PIB/CCI ingest; no event table |
| `procurement_volume_mt_mtd` | **No** | No volume source |
| `export_restriction_flag` | **No** | No ministry circular ingest |
| PIB announcement dates | **No** | Manual / future ingest |

### 6.2 Gaps vs SIGNAL_ENGINE_V1

| Component | Confidence tier (spec) | Gap |
|-----------|------------------------|-----|
| `msp_inr_quintal` | 0.85–0.95 if PIB-sourced | MSP not seeded — cannot reach high tier |
| `spot_vs_msp_pct` | Derived | Needs MSP + fresh modal across basket |
| `cci_active_procurement` | Floor / MSP_FLOOR regime | **No machine-readable CCI API** ([PROCUREMENT_SIGNAL_MODEL.md](./PROCUREMENT_SIGNAL_MODEL.md) §4) |
| Staleness decay | Hold last known | No policy event stream to hold |
| Decision `msp_proximity_triggered` | Spot ±3% vs MSP | Same MSP gap |

**Partial path today:** If founder supplies **MSP INR/quintal** into registry `decision_rules` (one-time seed) **and** Agmarknet production load provides **current modal**, Policy agent could emit **registry + derived spot only** signal at **0.60–0.75** confidence band (spec §5.5) — still **no** CCI/export/volume.

### 6.3 Minimum additional ingest (Policy → **READY**)

| # | Deliverable | Owner |
|---|-------------|-------|
| P-1 | **`msp_inr_quintal`** (or equivalent) in active registry `decision_rules` + update process on PIB MSP events | E-02 / ops |
| P-2 | **Daily Agmarknet modal** (same as M-1) for `spot_vs_msp_pct` | E-03 |
| P-3 | **PIB RSS/HTML ingest** (or structured manual entry) for CCI window + MSP announcements | E-03 / Policy track |
| P-4 | **CCI active flag + geography[]** from notices | E-03 |
| P-5 | **Procurement volume MTD** — monthly hold-forward with staleness metadata | E-03 |
| P-6 | **Export restriction** circular status | E-03 |

**Minimum for PARTIAL → elevated confidence:** P-1 + P-2 only (derived floor proximity without CCI).

### 6.4 E-04 blockers (Policy-specific)

| Blocker | Severity |
|---------|----------|
| SI-05 MSP absolute | **Hard** for `spot_vs_msp_pct` and MSP_FLOOR |
| SI-06 PIB/CCI/export | **Hard** for procurement magnitude and `cci_active_procurement` |
| SI-03 spot history | **Soft** — single-day spot still computable |
| Optional agent | **Soft** for MI publish |

**Verdict: PARTIAL** — price observations enable **future** spot derivation; **policy event and MSP inputs are not observation-ready**.

---

## 7. Cross-Cutting: Futures, Quality, Partitions

These gaps affect **E-04 orchestration** beyond the three agents in Track E scope.

### 7.1 DS-001 / Futures (SI-01)

| Item | Status |
|------|--------|
| Founder sign-off | **OPEN** — [DS001_FOUNDER_DECISION_PACKAGE.md](./DS001_FOUNDER_DECISION_PACKAGE.md) |
| `FuturesObservation` ingest | **Not started** |
| `data_quality_snapshot.futures_feed_ok` | Defaults exist in schema; **not set by ingest** |
| Cotton `required_agents` | **Market + Futures** — strict snapshot validation **fails** without Futures row |

Market agent **basis fallback** (FD-030) and Futures agent §6 remain **BLOCKED** until DS-001 Option B closes.

### 7.2 Partition backfill (SI-07 / E-03 G7)

| Partition child | Range | PI5 data impact |
|-----------------|-------|-----------------|
| `price_observation_2026_06` | 2026-06-01 → 2026-07-01 | Warangal `2026-06-04` → named partition |
| `price_observation_default` | catch-all | Khammam `2022-03-26` proof lands here |
| Future months | **Not created** | 24/36 mo Agmarknet + weather bootstrap needs **forward migrations** |

Ops replay and backtests spanning multiple years require explicit partition DDL — not automatic from DEFAULT alone for query planning at scale.

### 7.3 `data_quality_snapshot` (SI-04)

Required for Market confidence and Futures feed health ([E03_SPRINT0_AUDIT.md](../reviews/E03_SPRINT0_AUDIT.md) G8). **No ingest writer** → E-04 agents cannot apply spec penalties from live quality rows.

---

## 8. E-04 Readiness Matrix (Consolidated)

| Agent | Observations today | Registry today | Min ingest to **READY** | E-04 can start wiring? |
|-------|-------------------|----------------|-------------------------|------------------------|
| **Market** | 8 sparse Agmarknet rows | Basket + sources OK | M-1–M-6 | **Yes (degraded)** — not production MI |
| **Weather** | **0** | Variable names only | W-1–W-6 | **No** — blocked on observation store |
| **Policy** | Spot derivable only | Proximity % only; no MSP INR | P-1–P-6 (P-1+P-2 minimal partial) | **Yes (low confidence)** — no MSP_FLOOR |
| **Futures** (required) | **0** | N/A | DS-001 + licensed EOD | **Degraded stub only** |
| **Orchestration** | — | `required_agents` | SI-01 + all required inputs | **Strict path blocked** |

---

## 9. Recommendations (Research Only)

| Priority | Action | Unblocks |
|----------|--------|----------|
| 1 | Close **DS-001** (Option B) + futures observation schema/ingest | Required-agent gate; Market basis fallback |
| 2 | **E-03 Sprint 0** Agmarknet production + **30d+ backfill** + quality snapshot | Market **READY**; Policy spot |
| 3 | Add **MSP** to registry `decision_rules` + PIB/CCI ingest design | Policy **READY** |
| 4 | Weather **DDL + NASA POWER dev load** → IMD PRIMARY after WS-01 | Weather **READY** (tiered confidence) |
| 5 | **Partition forward migrations** (G7) before large backfill | SI-07 |

**Do not** claim E-04 production-ready MI until: **Futures licensed path** + **Market history/quality** + explicit non-production label for Weather/Policy until P-1/W-1 complete.

---

## 10. Traceability

| Section | Sources |
|---------|---------|
| §3 Inventory | [OBSERVATION_POPULATION_REPORT.md](../reviews/OBSERVATION_POPULATION_REPORT.md) |
| §4 Market | [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §3, [AGMARKNET_SPIKE_REPORT.md](../reviews/AGMARKNET_SPIKE_REPORT.md), [E03_SPRINT0_AUDIT.md](../reviews/E03_SPRINT0_AUDIT.md) |
| §5 Weather | [WEATHER_SPIKE_REPORT.md](../reviews/WEATHER_SPIKE_REPORT.md), [WEATHER_DATA_STRATEGY_V1.md](./WEATHER_DATA_STRATEGY_V1.md) |
| §6 Policy | [PROCUREMENT_SIGNAL_MODEL.md](./PROCUREMENT_SIGNAL_MODEL.md), [COTTON_INTELLIGENCE_MODEL_V1.md](./COTTON_INTELLIGENCE_MODEL_V1.md) §6 |
| §7 Cross-cutting | [DS001_FOUNDER_DECISION_PACKAGE.md](./DS001_FOUNDER_DECISION_PACKAGE.md), `0005_observations_partitioned.py` |
| Registry | [`cotton.json`](../../backend/app/persistence/seeds/fixtures/cotton.json) |

---

*End of Signal Input Readiness — PI5 Track E.*
