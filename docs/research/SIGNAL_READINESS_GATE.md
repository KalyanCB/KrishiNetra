# Signal Readiness Gate — PI7 Track G

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI7 Track G (KDO — research only; no signal runtime) |
| **Epic** | E-04 Domain Agents — **input readiness gate** (post PI7 Tracks A–F) |
| **Scope** | Market, Weather, Policy readiness; E-04 start verdict; path to `overall_quality_score` **> 0.70** |
| **Out of scope** | Signal runtime, LangGraph orchestration, Futures/Global implementation, dashboard UI |
| **Baseline docs** | [SIGNAL_READINESS_ASSESSMENT.md](./SIGNAL_READINESS_ASSESSMENT.md) (PI6 Track G), [OBSERVATION_COVERAGE_GAPS.md](./OBSERVATION_COVERAGE_GAPS.md) (PI7 Track F), [E03_S02_COMPLETION_REPORT.md](../reviews/E03_S02_COMPLETION_REPORT.md), [DATA_QUALITY_REPORT.md](../reviews/DATA_QUALITY_REPORT.md) |
| **Quality trend** | [DATA_QUALITY_TREND_REPORT.md](../reviews/DATA_QUALITY_TREND_REPORT.md) (PI7 Track E) |

---

## 1. Executive Summary

PI7 closes the **cotton belt observation engineering loop**: **27** Agmarknet mandis seeded (Track B), **8,792** fixture backfill rows across a **1,099-day** window (Track A / E-03-S02), **5,620** NASA POWER weather rows (Track D), and DQS wired with `overall_quality_score` **0.3161** @ `127.0.0.1:5433`. **Live OGD remains blocked** (`OGD_API_KEY` absent; demo key unauthorised).

| Question | Gate answer |
|----------|-------------|
| **Signal-ready (production)?** | **No** — belt Market/Policy transforms and cross-agent MI remain **non-production** |
| **E-04 can start?** | **Yes — degraded mode** (agent wiring, neutral/low-confidence stubs, AC-01/AC-06 harness) |
| **Strict `SignalSnapshot` → Forecast?** | **No** — `required_agents: ["Market","Futures"]`; Futures **BLOCKED** (DS-001); Market **not spec-ready** for §3.2 z-scores on 4-mandi basket |

### PI6 → PI7 delta (observation depth)

| Dimension | PI6 @ 5433 | PI7 @ 5433 | Signal impact |
|-----------|------------|------------|---------------|
| Mandis expected (DQS) | 4 (TG primary) | **27** (belt) | Denominator widened; coverage ratio fell |
| Price/arrival rows | ~8 proof-scale | **8,792** fixture | Calendar **completeness** → 1.0; **market coverage** still 2/27 |
| Distinct trade dates (2 mandis) | 2 | **1,099** each | Per-market history deep; **basket** still 2/4 TG, 2/27 belt |
| `overall_quality_score` | 0.0617 | **0.3161** | Up, but **< 0.70** gate |
| Weather NASA rows | 5,620 | **5,620** | Unchanged — Weather tier-2 **READY** |
| Live Agmarknet | Not run | **Still blocked** (OGD key) | SR-01 / OC7-01 unchanged |

---

## 2. PI7 Integration Snapshot (@ 5433)

Synthesized from [E03_S02](../reviews/E03_S02_COMPLETION_REPORT.md), [OBSERVATION_COVERAGE_GAPS](./OBSERVATION_COVERAGE_GAPS.md), [NASA_POWER_BACKFILL_REPORT](../reviews/NASA_POWER_BACKFILL_REPORT.md).

| Check | Result |
|-------|--------|
| `alembic_version` | `0010_partition_backfill` |
| Cotton belt markets seeded | **27** (`load_expected_market_ids`) |
| Markets with ≥1 price row (belt scope) | **2 / 27** (`mkt_tg_khammam_apmc`, `mkt_tg_warangal`) |
| TG primary (4 mandis) with data | **2 / 4** — Karimnagar, Kesamudram **empty** |
| Backfill window | `2023-06-01` → `2026-06-03` (**1,099** days) |
| Fixture observation rows | **8,792** (7,693 price + 1,099 arrival) |
| `weather_observation` (`nasa_power`) | **5,620** — `2023-05-01` → `2026-05-31`, 5 TG `region_id`s |
| `data_quality_snapshot` (post E-03-S02 belt fixture) | `overall_quality_score` **0.3161**; `coverage_ratio` **0.074**; `completeness_ratio` **1.0**; `anomaly_count` **8,792** |
| `OGD_API_KEY` | **Absent** — live backfill **BLOCKED** |
| Futures / policy event observations | **0** |

**Interpretation:** Fixture replay fills **every calendar day** for two Telangana mandis but **does not** populate the other **25** belt mandis or **live** multi-state OGD tuples. DQS **0.3161** reflects high completeness on a sparse market denominator plus **maximum anomaly penalty** (all rows non-`VALIDATED`).

---

## 3. Domain Readiness Verdicts

| Domain | Verdict | One-line rationale |
|--------|---------|-------------------|
| **Market** | **PARTIAL** | Ingest + 36-mo fixture **READY** (code/data path); §3.2 **4-mandi basket** and belt dispersion **NOT READY** (2/27 mandis; 2/4 TG primary) |
| **Weather** | **PARTIAL** | NASA tier-2 corpus **READY** (5,620 rows); IMD PRIMARY **NOT READY**; belt geography + joint mandi joins **NOT READY** |
| **Policy** | **PARTIAL** | Spot path **minimal** (2-mandi modal); `msp_inr_quintal`, CCI/PIB **NOT READY** |

### 3.1 Market — **PARTIAL**

| Capability | Status | PI7 evidence |
|------------|--------|--------------|
| Production OGD pipeline + belt backfill CLI | **READY** (code) | E-03-S02; `agmarknet_backfill.py --scope belt` |
| 36-mo calendar density (reporting mandis) | **READY** (fixture) | 1,099 distinct `as_of_date` per Khammam + Warangal |
| 4-mandi TG primary basket | **NOT READY** | 2/4 mandis; z-score window needs **≥30d × 4** ([E03_S02](../reviews/E03_S02_COMPLETION_REPORT.md)) |
| Belt `primary_markets_reporting_pct` | **NOT READY** | 2/27 ≈ **7.4%** coverage on latest trade date |
| `price_trend_zscore` / `arrival_zscore` (spec basket) | **BLOCKED** | Basket incomplete; arrivals season coverage unproven across 4 mandis |
| DQS confidence inputs (`agmarknet_lag_hours`) | **PARTIAL** | Writer works; score penalized by coverage + anomalies |
| Futures basis fallback | **BLOCKED** | DS-001 / SR-02 |

**Degraded E-04:** Neutral direction / near-zero magnitude from sparse basket — **wiring only** ([SIGNAL_INPUT_READINESS.md](./SIGNAL_INPUT_READINESS.md) §4.3).

### 3.2 Weather — **PARTIAL**

| Capability | Status | PI7 evidence |
|------------|--------|--------------|
| `weather_observation` store + NASA backfill | **READY** | 5,620 rows; Track D **PASS** |
| Weather agent AC-05 `source_refs[]` (tier-2) | **READY** | 36-mo series per 5 TG districts |
| IMD PRIMARY anomalies / categories | **NOT READY** | WS-01 API key |
| Belt MH/GJ/AP/KA gridded weather | **NOT READY** | **22** belt mandis lack NASA rows in DB |
| Joint price–weather features | **NOT READY** | Mandi series concentrated in 2 markets; no explicit market↔region FK ([OC7-03](./OBSERVATION_COVERAGE_GAPS.md)) |

**Optional agent** — omission penalizes MI confidence but does not abort pipeline (`optional_agents` in cotton registry).

### 3.3 Policy — **PARTIAL**

| Input | Status | PI7 evidence |
|-------|--------|--------------|
| Spot modal (Agmarknet-derived) | **Minimal** | 2 mandis × dense dates; not belt-representative |
| `msp_inr_quintal` | **NOT READY** | Absent @ `cotton.json` v1.0.0 |
| `spot_vs_msp_pct` | **NOT READY** | Needs MSP + fresh 4-mandi basket |
| `cci_active_procurement` / export flags | **NOT READY** | No PIB/CCI ingest (SR-03) |

**Low-confidence Policy stub** possible only after **SR-03** (MSP seed) **and** SR-01 live corpus for current modal — not met @ PI7.

---

## 4. Cross-Cutting Gates

### 4.1 Required agents (orchestration)

From [`cotton.json`](../../backend/app/persistence/seeds/fixtures/cotton.json):

```json
"required_agents": ["Market", "Futures"]
```

| Agent | PI7 input readiness | E-04 strict gate |
|-------|---------------------|------------------|
| **Market** | **PARTIAL** | Degraded signal possible; **not** spec-compliant MI |
| **Futures** | **BLOCKED** (DS-001) | **Hard fail** — no strict MI publish ([SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md) §8) |

### 4.2 Data quality (@ 5433)

| Metric | Post E-03-S02 fixture | Target |
|--------|----------------------|--------|
| `overall_quality_score` | **0.3161** | **> 0.70** |
| `coverage_ratio` | **0.074** (2/27) | **≥ 0.70** (~19+ mandis on latest date) |
| `completeness_ratio` | **1.0** (1099/1099 days with belt-union data) | Maintained under live load |
| `anomaly_penalty` | **~0.30** (max; 8,792/8,792 non-validated) | Near **0** after validation pipeline |

Formula ([`metrics.py`](../../backend/app/services/quality/metrics.py)):

```
score = 0.40 × coverage_ratio + 0.35 × completeness_ratio + 0.25 × freshness − anomaly_penalty
```

Fixture mode already maximizes **completeness**; **> 0.70** on the 36-mo snapshot requires **belt market coverage** and **validated rows**, not more calendar days alone.

### 4.3 Gap IDs (consolidated)

| ID | Gap | PI7 status |
|----|-----|------------|
| **SR-01** / **OC7-01** | Live 36-mo Agmarknet (OGD key) | **OPEN** |
| **OC7-02** | 25/27 belt mandis empty | **OPEN** |
| **OC7-03** | Weather geography + joint alignment | **OPEN** |
| **SR-02** | DS-001 Futures unsigned | **OPEN** |
| **SR-03** | MSP + PIB/CCI policy ingest | **OPEN** |
| **SI-02** | Weather persistence | **CLOSED** (PI6/PI7) |
| **SI-04** | DQS writer | **CLOSED** (scores low until SR-01 + validation) |

---

## 5. Path to `overall_quality_score` > 0.70

*Progression from [DATA_QUALITY_TREND_REPORT.md](../reviews/DATA_QUALITY_TREND_REPORT.md) and [OBSERVATION_COVERAGE_GAPS](./OBSERVATION_COVERAGE_GAPS.md) §7.*

| Stage | Score | Driver |
|-------|-------|--------|
| PI6 DQS sample (4 mandis, 30d window) | **0.0617** | 1/4 coverage, 1/30 completeness |
| PI7 post fixture (27 mandis, 1099d window) | **0.3161** | Completeness **1.0**, coverage **0.074**, anomaly penalty **~0.30** |
| Target (live belt) | **> 0.70** | **≥19/27** reporting + validated rows + sustained freshness |

### 5.1 What must change (ordered)

| # | Action | Closes | Why it matters for score |
|---|--------|--------|---------------------------|
| **1** | Register `OGD_API_KEY`; run live `agmarknet_backfill.py --scope belt` | SR-01, OC7-01, OC7-02 | Raises **coverage_ratio** toward ≥0.70 (19+ mandis) |
| **2** | OGD 90-day audit + tuple fixes per [MARKET_COVERAGE_REPORT](../reviews/MARKET_COVERAGE_REPORT.md) | OC7-02 | Prevents silent zero-row states (MH/GJ/AP/KA) |
| **3** | Normalize ingest validation status (`VALIDATED` / `PUBLISHED`) | OC7-06 | Removes **0.30** anomaly ceiling on 8k+ rows |
| **4** | TG-first: populate Karimnagar + Kesamudram (fixture extension or live) | Market §3.2, Policy spot | 4/4 primary basket for z-scores (orthogonal to belt 0.70 but **required for signals**) |
| **5** | Ops: daily `record_after_agmarknet_ingest` (30d window) | Path C in OC gaps | Rolling DQS ≈ **0.95** when 4/4 × 30/30 — better **ops gate** than 36-mo archive denominator |
| **6** | Founder **DS-001** + futures ingest | SR-02 | Strict E-04 orchestration (not a DQS term) |
| **7** | `msp_inr_quintal` + PIB/CCI design | SR-03 | Policy production tiers |

**Do not** treat **0.3161** or fixture calendar fill as signal readiness — **coverage** and **validation** dominate the score; **Market z-scores** still need **4 TG mandis × ≥30 trading days** with real cotton tuples, not Warangal non-cotton mapping alone.

---

## 6. E-04 Start Decision Matrix

| Path | Can start @ PI7? | Production MI? |
|------|------------------|----------------|
| Agent implementation + unit transforms | **Yes** | No |
| Degraded Market/Policy stubs | **Yes** | No |
| Weather agent (tier-2 NASA) | **Yes** (label non-production) | Partial confidence only |
| Futures agent (required) | **Stub only** | **Blocked** |
| Strict `SignalSnapshot` → Forecast | **No** | **Blocked** |

### 6.1 Minimum work before production-grade E-04 signals

| Order | Deliverable | Closes |
|-------|-------------|--------|
| 1 | Live OGD belt backfill @ 5433 + `--stats --write-report` | SR-01, OC7-01/02, DQS >0.70 path |
| 2 | 4/4 TG primary mandis + ≥30d basket for §3.2 | Market **READY** (strict) |
| 3 | Daily Agmarknet + DQS refresh (cron / runbook) | SI-08 |
| 4 | DS-001 + licensed futures observations | SR-02 |
| 5 | MSP registry + PIB/CCI ingest | SR-03 |
| 6 | NASA (or IMD) for MH/GJ/AP/KA before belt MI | OC7-03 |

---

## 7. Overall Gate Verdict

| Gate | Result |
|------|--------|
| **Market** | **PARTIAL** |
| **Weather** | **PARTIAL** |
| **Policy** | **PARTIAL** |
| **Signal-ready (production)** | **NOT READY** |
| **E-04 start (degraded)** | **ALLOWED** |
| **E-04 strict / MI publish** | **BLOCKED** |
| **DQS > 0.70 @ 36-mo belt snapshot** | **NOT MET** (0.3161) |

### Top 3 blockers

| Rank | Blocker | Blocks |
|------|---------|--------|
| **1** | **OGD key + live belt backfill** (SR-01 / OC7-01) — 25/27 mandis empty; fixture cannot simulate MH/GJ/AP/KA | Market z-scores, Policy spot, **coverage_ratio** for DQS >0.70 |
| **2** | **Row validation / anomaly penalty** — 8,792/8,792 non-validated rows cap DQS even with completeness 1.0 | **> 0.70** score; Market confidence penalties |
| **3** | **DS-001 Futures unsigned** (SR-02) + **4-mandi TG gap** (2/4 reporting) | Strict `required_agents`; §3.2 basket transforms |

---

## 8. Traceability

| Section | Sources |
|---------|---------|
| §1–2 PI7 state | User PI7 payload, E03_S02, OBSERVATION_COVERAGE_GAPS |
| §3 Domains | SIGNAL_READINESS_ASSESSMENT (PI6), SIGNAL_ENGINE_V1 §3–§5, SIGNAL_INPUT_READINESS |
| §4–5 DQS | DATA_QUALITY_REPORT, E03_S02 §4, `metrics.py`, OBSERVATION_COVERAGE_GAPS §7 |
| §6 E-04 | PI6_EXECUTIVE_SUMMARY, SIGNAL_ENGINE_V1 §8–§10, cotton.json |
| §7 Verdict | This synthesis |

---

*End of Signal Readiness Gate — PI7 Track G.*
