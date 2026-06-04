# Signal Readiness Assessment — PI6 Track G

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI6 Track G (KDO — research only; no signal runtime) |
| **Epic** | E-04 Domain Agents — input readiness gate |
| **Scope** | Market, Weather, Policy signal inputs after PI6 Tracks A–F; cotton registry; E-04 start verdict |
| **Out of scope** | Signal runtime, LangGraph orchestration, Futures/Global agent implementation, dashboard UI |
| **Baseline docs** | [OBSERVATION_COVERAGE_ANALYSIS.md](./OBSERVATION_COVERAGE_ANALYSIS.md), [SIGNAL_INPUT_READINESS.md](./SIGNAL_INPUT_READINESS.md), [DATA_QUALITY_REPORT.md](../reviews/DATA_QUALITY_REPORT.md), [HISTORICAL_BACKFILL_REPORT.md](../reviews/HISTORICAL_BACKFILL_REPORT.md), [NASA_POWER_INGESTION_REPORT.md](../reviews/NASA_POWER_INGESTION_REPORT.md), [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) |

---

## 1. Executive Summary

PI6 Tracks **A–F** close the **engineering path** for cotton observations: production Agmarknet pipeline (Track A), 36-month backfill framework + partition `0010` (Track B), NASA POWER persistence **5,620** rows @ `0009` (Track D), and `data_quality_snapshot` ingest wiring (Track E). **Signal-ready depth for Market and Policy remains absent on the integration DB** — price/arrival counts are still **proof-scale** (7 + 1 rows, **2** trading dates, **2 / 4** mandis), not the ~1,095-day × 4-mandi corpus the backfill CLI targets.

| Signal | PI5 verdict | PI6 verdict | Delta |
|--------|-------------|-------------|-------|
| **Market** | PARTIAL | **PARTIAL** (observations **BLOCKED** for §3.2 features) | +prod pipeline, +DQS writer; −history depth unchanged @ 5433 |
| **Weather** | BLOCKED | **PARTIAL** | +`weather_observation` DDL + 5,620 NASA rows; IMD PRIMARY still open |
| **Policy** | PARTIAL | **PARTIAL** | Spot path unchanged; MSP/CCI/PIB still missing |

### E-04 verdict (one line)

**E-04 can start in degraded mode** (agent wiring, neutral/low-confidence stubs, AC-01/AC-06 harness). **Production-grade Market/Policy transforms and strict `SignalSnapshot` publish remain blocked** until live Agmarknet backfill, **DS-001** Futures, and registry MSP.

### Top 3 gaps (priority)

| Rank | Gap ID | Gap | Blocks |
|------|--------|-----|--------|
| **1** | **SR-01** | **Live 36-month Agmarknet backfill not executed** on integration DB — 2 dates / 2 mandis vs ≥30d z-score window | `price_trend_zscore`, `arrival_zscore`, `primary_markets_reporting_pct`; Policy `spot_vs_msp_pct`; joint weather–mandi features |
| **2** | **SR-02** | **Futures feed unsigned (DS-001 / SI-01)** — no licensed EOD observations | Cotton `required_agents: ["Market","Futures"]`; strict MI gate ([SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §8); Market basis-fallback confidence |
| **3** | **SR-03** | **`msp_inr_quintal` absent** + **no PIB/CCI/export policy ingest** | Policy `spot_vs_msp_pct`, MSP_FLOOR regime, `cci_active_procurement` high-confidence tiers |

---

## 2. PI6 Foundation vs Observation Depth

Tracks A–F deliver **repeatable ingest**, not by themselves a **signal corpus**.

| Track | Deliverable | Signal impact |
|-------|-------------|---------------|
| **A** | Production `AgmarknetIngestPipeline`, dedupe, CLI ([E03_S01_COMPLETION_REPORT.md](../reviews/E03_S01_COMPLETION_REPORT.md)) | Enables daily refresh; **does not** populate 36 mo history without ops run |
| **B** | `agmarknet_backfill.py`, migration `0010`, fixture/idempotent tests ([HISTORICAL_BACKFILL_REPORT.md](../reviews/HISTORICAL_BACKFILL_REPORT.md)) | **Framework PASS**; live row counts **ops-dependent** (`OGD_API_KEY` or bulk zip) |
| **D** | NASA POWER → `weather_observation` ([NASA_POWER_INGESTION_REPORT.md](../reviews/NASA_POWER_INGESTION_REPORT.md)) | Closes **SI-02**; Weather agent can read 36-mo tier-2 series |
| **E** | `DataQualitySnapshotService` post Agmarknet/weather ([DATA_QUALITY_REPORT.md](../reviews/DATA_QUALITY_REPORT.md)) | Closes **SI-04** wiring; scores reflect **sparse** mandi data until SR-01 |
| **F** | [OBSERVATION_COVERAGE_ANALYSIS.md](./OBSERVATION_COVERAGE_ANALYSIS.md) | Documents joint-coverage gap (weather dense, mandi empty/sparse) |

**Rule (unchanged from PI5):** Signal readiness requires **queryable, aligned time series** per [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md), not spike-only or registry-only fields.

---

## 3. Live Integration Snapshot (@ 5433, 2026-06-04)

Queried `postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra` for this assessment.

| Check | Result |
|-------|--------|
| `alembic_version` | `0010_partition_backfill` |
| `price_observation` (cotton, `agmarknet`) | **7** — `2022-03-26` … `2026-06-04`, **2** distinct dates |
| `arrival_observation` (cotton) | **1** — Khammam `2022-03-26` only |
| Markets with ≥1 price row | **2 / 4** (`mkt_tg_khammam_apmc`, `mkt_tg_warangal`) |
| `weather_observation` (`nasa_power`) | **5,620** — `2023-05-01` … `2026-05-31`, 5 regions × 1,124 days |
| `data_quality_snapshot` | **1** — `overall_quality_score` **0.0617**, `agmarknet_lag_hours` **0.0**, coverage **1/4** markets, **1/30** days in window |
| Futures / policy event tables | **0** |

**Reconcile with Track F note:** Weather-only load scenarios are superseded here by **proof-scale Agmarknet + weather + one DQS row** on the same DB; full backfill has **not** been run (`--stats --write-report` still pending per backfill report §7).

---

## 4. Market Signal Readiness

**Spec:** [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §3 — modal/min/max, arrivals, basket, `DataQualitySnapshot`, optional Futures basis fallback.

### 4.1 What PI6 unlocked

| Capability | Status | Evidence |
|------------|--------|----------|
| Production OGD fetch + dedupe + persist | **READY** (code) | Track A pipeline + tests |
| Historical backfill CLI + partitions | **READY** (code) | Track B; `0010` on DB |
| Quality snapshot after ingest | **READY** (wired) | Track E; 1 row @ 5433 |
| Daily `DATA_REFRESH_START` cron | **Not shipped** | CLI/manual only (inherits SI-08) |

### 4.2 Observation state vs §3.2 transforms

| Feature / input | Requirement | @ 5433 | Readiness |
|-----------------|-------------|--------|-----------|
| `price_trend_zscore` | 30d rolling modal (4-mandi basket) | Max **1** day/market | **BLOCKED** |
| `arrival_zscore` | Seasonal norm; Oct–Mar (FG-01) | **1** day (Mar 2022) | **BLOCKED** |
| `regional_strength_index` | Multi-market × multi-day | 2 markets × 1 day | **BLOCKED** |
| `primary_markets_reporting_pct` | Daily basket series | 50% ever; not daily | **BLOCKED** |
| Confidence `λ_lag` | `agmarknet_lag_hours` from DQS | **Present** (0.0 h) | **PARTIAL** — formula inputs exist; coverage penalty dominates |
| Basis fallback | Licensed futures | DS-001 open | **BLOCKED** |

### 4.3 Verdict: **PARTIAL**

- **Infrastructure:** READY for E-04 to **load observations** and apply confidence from DQS.
- **Deterministic daily Market signal per spec:** **not READY** until **SR-01** (executed backfill + sustained daily ingest) and ideally **SR-02** for basis path.

**Degraded E-04 path:** Emit neutral direction, near-zero magnitude, very low confidence from sparse rows — useful for **wiring tests only** ([SIGNAL_INPUT_READINESS.md](./SIGNAL_INPUT_READINESS.md) §4.3).

---

## 5. Weather Signal Readiness

**Spec:** [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §4 — IMD PRIMARY, NASA gap-fill, registry `weather_variables`, climatology.

### 5.1 What PI6 unlocked

| Capability | Status | Evidence |
|------------|--------|----------|
| Weather observation store (`0009`) | **READY** | Migration + repository |
| 36-mo NASA POWER backfill | **READY** (data) | 5,620 rows; 5 Telangana districts |
| `rainfall` / humidity proxy | **PARTIAL** | `rainfall_mm`, `relative_humidity_pct` persisted; registry `acreage` not ingested |
| IMD departure/category anomalies | **BLOCKED** | WS-01 API key; WS-04 semantic gap |
| Joint price–weather features | **BLOCKED** | Mandi calendar empty/sparse (SR-01 + OC-04 alignment) |

### 5.2 Registry vs stored variables

| `weather_variables` (cotton v1.0.0) | Persisted |
|-------------------------------------|-----------|
| `rainfall` | `rainfall_mm` |
| `humidity` | `relative_humidity_pct` |
| `acreage` | Not ingested |

### 5.3 Verdict: **PARTIAL**

- **SI-02 closed** — Weather agent can satisfy **AC-05** `source_refs[]` to E-03 observations for tier-2 NASA series.
- **Production-grade** rainfall anomaly / IMD category features: **BLOCKED** on WS-01 until IMD PRIMARY.
- **Optional agent** — omission penalizes MI confidence but does not abort pipeline ([`cotton.json`](../../backend/app/persistence/seeds/fixtures/cotton.json) `optional_agents`).

**Calendar skew:** Weather starts `2023-05-01`; Agmarknet backfill default `2023-06-01` — align on SR-01 execution ([OBSERVATION_COVERAGE_ANALYSIS.md](./OBSERVATION_COVERAGE_ANALYSIS.md) OC-04).

---

## 6. Policy Signal Readiness

**Spec:** [SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §5 — MSP, spot vs MSP, CCI procurement, export restrictions.

### 6.1 Data available today

| Input | Available? | Evidence |
|-------|------------|----------|
| Spot modal (Agmarknet-derived) | **Minimal** | 7 price rows; 2 dates; 2 markets |
| `msp_inr_quintal` | **No** | `decision_rules` has `msp_proximity_pct` only @ v1.0.0 |
| `spot_vs_msp_pct` | **No** | Needs MSP absolute + fresh basket modal |
| `cci_active_procurement` | **No** | No PIB/CCI ingest |
| Procurement volume / export flags | **No** | No event tables |

### 6.2 Verdict: **PARTIAL**

- **Low-confidence path:** Possible if founder seeds **MSP INR/quintal** (SR-03 partial) **and** SR-01 delivers current modal — spec band **0.60–0.75** without CCI ([SIGNAL_INPUT_READINESS.md](./SIGNAL_INPUT_READINESS.md) §6.2).
- **MSP_FLOOR / high-confidence procurement:** **BLOCKED** on SR-03 + SR-01.

---

## 7. Cross-Cutting E-04 Gates

### 7.1 Required agents (orchestration)

From [`cotton.json`](../../backend/app/persistence/seeds/fixtures/cotton.json):

```json
"required_agents": ["Market", "Futures"]
```

| Agent | PI6 input readiness | E-04 strict gate |
|-------|---------------------|------------------|
| **Market** | PARTIAL (sparse history) | Degraded signal possible; **not** spec-compliant MI narrative |
| **Futures** | **BLOCKED** (DS-001) | **Hard fail** — missing required agent → no MI publish ([SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §8 step 5) |

### 7.2 Data quality snapshot (Track E)

| Field | @ 5433 | Interpretation |
|-------|--------|----------------|
| `overall_quality_score` | 0.0617 | Reflects **1/30** day completeness, **1/4** market coverage |
| `agmarknet_lag_hours` | 0.0 | Writer works; lag meaningful only with production refresh cadence |
| `source_health.agmarknet` | `stale` | Consistent with SR-01 |

Track E **unblocks the Market confidence formula structurally**; scores will remain low until mandi history depth improves.

### 7.3 Joint coverage (Track F)

| Dimension | Weather | Mandi price/arrival |
|-----------|---------|---------------------|
| Row density | **High** (5,620) | **Low** (8 total facts) |
| Date overlap for joins | 1,124 days | **2** days |
| Geographic pairing | 5 `region_id`s; 4 mandis (implicit district map) | No observation-level FK |

**Belt-level Weather signal:** feasible on NASA alone. **Cross-agent MI features** (rain during high-arrival weeks, price–weather correlation): **BLOCKED** until SR-01.

---

## 8. E-04 Start Decision Matrix

| Path | Can start? | Conditions | Production MI? |
|------|------------|------------|----------------|
| **Agent implementation + unit transforms** | **Yes** | Use fixtures + degraded neutral outputs when z-scores undefined | No |
| **Daily refresh orchestration hook** | **Partial** | Ingest CLIs exist; cron/scheduler still open (SI-08) | No |
| **Weather agent (optional)** | **Yes (tier-2)** | 5,620 NASA rows; label non-production without IMD | Partial confidence |
| **Policy agent (optional)** | **Yes (low)** | After SR-03 seed MSP; still no CCI without SR-3b ingest | Low confidence |
| **Futures agent (required)** | **Stub only** | DS-001 unsigned | Strict path **blocked** |
| **SignalSnapshot → Forecast handoff** | **No (strict)** | `required_agents` validation fails without Futures; Market not spec-ready | **Blocked** |

### 8.1 Minimum work before “production-ready” E-04 signals (research view)

| Order | Deliverable | Closes |
|-------|-------------|--------|
| 1 | Run `agmarknet_backfill.py` live on @ 5433; refresh backfill report `--stats --write-report` | SR-01, Market §3.2, Policy spot |
| 2 | Daily production Agmarknet + DQS refresh (cron or ops runbook) | SI-08, stable `λ_lag` |
| 3 | Founder **DS-001** + futures observation ingest | SR-02, strict gate |
| 4 | `msp_inr_quintal` in `decision_rules` + PIB/CCI design | SR-03 |
| 5 | IMD PRIMARY post WS-01 (optional agent tier-1) | Weather production tier |

**Do not** treat PI6 weather ingest alone as belt **signal readiness** — without mandi price/arrival on the same calendar, Market and cross-agent MI remain **non-production**.

---

## 9. Gap Consolidation (PI5 → PI6)

| ID | PI5 | PI6 status | Notes |
|----|-----|------------|-------|
| SI-01 Futures | BLOCKED | **BLOCKED** | Unchanged |
| SI-02 Weather persistence | BLOCKED | **CLOSED** | Track D |
| SI-03 Market history | BLOCKED | **BLOCKED** @ 5433 | Framework ready (SR-01) |
| SI-04 Quality snapshot | BLOCKED | **CLOSED** (wired) | Scores low until SR-01 |
| SI-05 MSP absolute | BLOCKED | **BLOCKED** | SR-03 |
| SI-06 PIB/CCI/export | BLOCKED | **BLOCKED** | SR-03 |
| SI-07 Partitions | BLOCKED | **CLOSED** | `0010` @ 5433 |
| SI-08 Production cadence | BLOCKED | **PARTIAL** | Pipeline yes; scheduler no |
| OC-01 Agmarknet history | — | **OPEN** | Same as SR-01 |
| OC-04 Calendar/region alignment | — | **OPEN** | After backfill |

---

## 10. Traceability

| Section | Sources |
|---------|---------|
| §2 PI6 tracks | E03_S01, HISTORICAL_BACKFILL, NASA_POWER, DATA_QUALITY reports |
| §3 Live counts | SQLAlchemy @ 5433 (2026-06-04) |
| §4–§6 Agents | SIGNAL_ENGINE_V1 §3–§5, SIGNAL_INPUT_READINESS, OBSERVATION_COVERAGE |
| §7 Orchestration | cotton.json, SIGNAL_ENGINE_V1 §8, DS001 package |
| §8 E-04 gate | SIGNAL_ENGINE_V1 §10 AC-01–AC-07 |

---

*End of Signal Readiness Assessment — PI6 Track G.*
