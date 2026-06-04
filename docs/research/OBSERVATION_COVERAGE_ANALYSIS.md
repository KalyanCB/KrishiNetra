# Observation Coverage Analysis — PI6 Track F

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI6 Track F (KDO — research only; no runtime code) |
| **Epic** | E-03 observation foundation → E-04 signal inputs |
| **Scope** | Cotton / Telangana belt: market vs seed, commodity coverage, date gaps, weather–mandi alignment, signal-readiness gaps |
| **Out of scope** | Dashboard UI, ingest implementation, signal runtime |

---

## 1. Executive Summary

PI6 has shipped **backfill framework** (Track B), **NASA POWER persistence** (Track D, 5,620 rows possible @ `127.0.0.1:5433`), and retains **PI5 proof** of Agmarknet → observation mapping (8 cotton rows in reports). **Signal-ready joint coverage does not exist:** the integration DB @ 5433 today has **dense weather** and **zero** Agmarknet price/arrival rows, so Market and Policy agents remain blocked on history depth while Weather moves from BLOCKED (PI5) to **data-rich but unpaired**.

| Dimension | Seed / registry | Reports (PI5–PI6) | Live @ `5433` (queried 2026-06-04) |
|-----------|-----------------|-------------------|-------------------------------------|
| Telangana mandis (markets) | **4** | 2 with any Agmarknet row | **4** seeded; **0** with price/arrival |
| Cotton price observations | Basket defined | 7 (`agmarknet`) | **0** |
| Cotton arrival observations | Agmarknet only | 1 | **0** |
| Weather observations | 5 district `region_id`s | 5,620 NASA POWER | **5,620** (`nasa_power`) |
| `data_quality_snapshot` | Schema @ `0004` | Not written | **0** rows |

### Top 3 priority gaps (signal readiness)

| Rank | Gap ID | Gap | Blocks |
|------|--------|-----|--------|
| **1** | **OC-01** | **No executed Agmarknet historical load** — 0 price/arrival @ 5433; framework only; PI5 proof not replayed on current DB | Market `price_trend_zscore`, `arrival_zscore`, `primary_markets_reporting_pct`; Policy `spot_vs_msp_pct`; DVA backtest mandi series |
| **2** | **OC-02** | **No `data_quality_snapshot` rows from ingest** | Market confidence `λ_lag` (`agmarknet_lag_hours`); futures feed health flags (E-03 G8) |
| **3** | **OC-03** | **Futures feed unsigned (DS-001 / SI-01)** + **`msp_inr_quintal` absent** in registry | Strict MI `required_agents` (Market + Futures); Policy MSP_FLOOR / high-confidence procurement |

**Secondary (cross-series):** **OC-04** — weather window starts `2023-05-01` vs Agmarknet backfill default `2023-06-01`; 5 weather districts vs 4 mandi markets (Nalgonda/Mahabubabad weather-only); no `market_id`↔`region_id` join in observation tables for joint features.

---

## 2. Validation Method

| Source | Use |
|--------|-----|
| [HISTORICAL_BACKFILL_REPORT.md](../reviews/HISTORICAL_BACKFILL_REPORT.md) | Track B framework, 36-mo window, 4 mandi triples |
| [OBSERVATION_POPULATION_REPORT.md](../reviews/OBSERVATION_POPULATION_REPORT.md) | PI5 proof counts (8 rows), FK chain, idempotency note |
| [NASA_POWER_INGESTION_REPORT.md](../reviews/NASA_POWER_INGESTION_REPORT.md) | Weather row counts, district mapping, 36-mo window |
| [SIGNAL_INPUT_READINESS.md](./SIGNAL_INPUT_READINESS.md) | Agent-level blockers (SI-01–SI-08) |
| [`cotton.json`](../../backend/app/persistence/seeds/fixtures/cotton.json) | 4 markets, 7 regions, registry agents/sources |
| Schema | `price_observation`, `arrival_observation` (`0005`); `weather_observation` (`0009`); partitions `0010` (backfill DDL on disk) |
| **Live DB** | `DATABASE_URL` → `postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra` — SQLAlchemy inventory (§3.4) |

**Rule:** Coverage for signals means **queryable, aligned time series** per agent spec ([SIGNAL_ENGINE_V1.md](./SIGNAL_ENGINE_V1.md)), not spike-only or registry-only fields.

---

## 3. Market Coverage vs Seeded Mandis

### 3.1 Seed baseline (E-02 `cotton.json`)

| `market_id` | Agmarknet triple | `region_id` |
|-------------|------------------|-------------|
| `mkt_tg_khammam_apmc` | Telangana / Khammam / Khammam | `reg_tg_khammam` |
| `mkt_tg_warangal` | Telangana / Warangal / Warangal | `reg_tg_warangal` |
| `mkt_tg_karimnagar` | Telangana / Karimnagar / Karimnagar | `reg_tg_karimnagar` |
| `mkt_tg_kesamudram` | Telangana / Khammam / Kesamudram | `reg_tg_kesamudram` |

Registry lists **Agmarknet** (+ eNAM, no rows) for prices and **Agmarknet** for arrivals. Basket size for Market agent = **4 primary mandis**.

### 3.2 Observation coverage by market

| `market_id` | PI5 proof ([OBSERVATION_POPULATION_REPORT](../reviews/OBSERVATION_POPULATION_REPORT.md)) | Post–Track B / live @ 5433 |
|-------------|----------------------------------------------------------------------------------------|----------------------------|
| `mkt_tg_khammam_apmc` | 3 price (min/max/modal) + 1 arrival @ `2022-03-26` | **0** rows |
| `mkt_tg_warangal` | 1 price (modal, Kapas→cotton) @ `2026-06-04` | **0** rows |
| `mkt_tg_karimnagar` | **0** | **0** rows |
| `mkt_tg_kesamudram` | **0** | **0** rows |

| Metric | PI5 proof | Live @ 5433 |
|--------|-----------|-------------|
| Markets with ≥1 price row | **2 / 4** (50%) | **0 / 4** (0%) |
| Markets with arrival row | **1 / 4** (Khammam only) | **0 / 4** |
| `primary_markets_reporting_pct` (daily series) | **Not computable** (2 snapshot dates) | **Not computable** |

**Verdict:** Seed **fully defines** the Telangana cotton basket; **observation coverage is empty** on the current integration DB and **sparse** even in the PI5 proof (half the basket, two non-contiguous dates).

### 3.3 Backfill framework vs loaded corpus

[Track B](../reviews/HISTORICAL_BACKFILL_REPORT.md) targets **36 calendar months** (`2023-06-01` → yesterday), per-day OGD `state=Telangana` + cotton mapper, production pipeline dedupe. Status: **PASS (framework)**; live national corpus = **ops-dependent** (`OGD_API_KEY` or zip bulk). No `--stats` refresh was run against @ 5433 for this analysis; Agmarknet counts above reflect direct table queries.

---

## 4. Commodity Coverage (Cotton Focus)

| Layer | Cotton-specific? | Evidence |
|-------|-------------------|----------|
| `commodity_id` | **Yes** — all seeded observations target `cotton` | Mapper filters cotton labels (incl. Kapas normalization) |
| Non-cotton OGD | **Dropped** | Maize @ unmapped `Dharmapuri APMC` → 0 drafts (PI5) |
| `price_type` | min / max / modal | 7 proof price rows |
| Quality | `quality_grade` from variety+grade | e.g. `Cotton\|FAQ` @ Khammam |
| Arrivals | Tonnes → quintals | 42.5 t → 425 quintal @ Khammam |
| Weather | `commodity_id=cotton` on all NASA rows | 5,620 rows @ 5433 |
| Futures / policy events | **None** | No tables populated |
| eNAM | Listed in registry | **0** rows |

**Cotton-only ingest path is proven**; **volume and diversity of cotton facts remain insufficient** for seasonal arrival z-scores (Oct–Mar window per [COTTON_INTELLIGENCE_MODEL_V1.md](./COTTON_INTELLIGENCE_MODEL_V1.md)) and for multi-market dispersion.

---

## 5. Date Coverage Gaps

### 5.1 Agmarknet (price + arrival)

| Window | PI5 proof | Track B target | Live @ 5433 |
|--------|-----------|----------------|-------------|
| Distinct `as_of_date` | **2** (`2022-03-26`, `2026-06-04`) | ~**1,095** days (36 mo from `2023-06-01`) | **0** |
| Contiguous trading-day series | **None** | Required ≥**30** days/market for z-scores | **None** |
| Arrival season (Oct–Mar) | **1** day in Mar 2022 only | Full seasons across backfill | **None** |
| Partition children (price) | `2026_06` + DEFAULT | `0010` adds `2023-06`…`2026-12` (on disk) | `2026_06` + DEFAULT only @ `0009` head |

**Gap OC-01:** Entire **2023-06 → present** mandi calendar is missing in Postgres despite backfill CLI/partition DDL readiness.

### 5.2 Weather (NASA POWER)

| Window | Track D / report | Live @ 5433 |
|--------|------------------|-------------|
| `as_of_date` span | `2023-05-01` → `2026-05-31` | **Same** |
| Distinct days per region | 1,124 | **1,124** × 5 regions |
| Source | `nasa_power` | **5,620** rows total |
| IMD PRIMARY | Not ingested | WS-01 gate unchanged |

**Gap OC-04:** One **calendar month skew** at start (weather May 2023 vs Agmarknet June 2023). End dates differ slightly (weather through May 2026 vs backfill “yesterday”). No overlapping price days to join.

### 5.3 Coverage dashboard (conceptual)

```mermaid
gantt
    title Cotton belt observation density (conceptual)
    dateFormat YYYY-MM-DD
    section Weather NASA
    reg_tg_* daily rows     :2023-05-01, 2026-05-31
    section Agmarknet price
    PI5 proof snapshots     :2022-03-26, 1d
    PI5 proof snapshots     :2026-06-04, 1d
    section Agmarknet target
    Track B 36mo window     :2023-06-01, 2026-06-03
```

---

## 6. Weather vs Price / Arrival Alignment

### 6.1 Geographic alignment

| `region_id` | Weather rows @ 5433 | Linked `market_id` | Price rows |
|-------------|---------------------|--------------------|------------|
| `reg_tg_khammam` | 1,124 | `mkt_tg_khammam_apmc`, `mkt_tg_kesamudram` (district Khammam) | 0 |
| `reg_tg_warangal` | 1,124 | `mkt_tg_warangal` | 0 |
| `reg_tg_karimnagar` | 1,124 | `mkt_tg_karimnagar` | 0 |
| `reg_tg_nalgonda` | 1,124 | *(no mandi in seed)* | — |
| `reg_tg_mahabubabad` | 1,124 | *(no mandi in seed)* | — |

- **Mandi without weather-exclusive region:** Kesamudram shares Khammam district → reasonable to attribute `reg_tg_khammam` weather; not modeled as explicit FK.
- **Weather without mandi:** Nalgonda, Mahabubabad — useful for belt-level Weather agent; **not** in 4-mandi Market basket.

### 6.2 Temporal alignment

| Join key | Weather | Price / arrival |
|----------|---------|-----------------|
| `as_of_date` | Daily 1,124 days | 0 days @ 5433 |
| `region_id` ↔ `market_id` | Implicit via seed geography only | No observation FK |
| Lag semantics | NASA T+2–3 ([WEATHER_DATA_STRATEGY_V1](./WEATHER_DATA_STRATEGY_V1.md)) | Agmarknet lag unmeasured (no `data_quality_snapshot`) |

**Joint feature readiness:** **BLOCKED** — Weather agent could compute rainfall/temperature anomalies on 36-mo series, but **cross-agent** features (e.g. rain during high-arrival weeks, price–weather correlation) need **aligned mandi dates** (OC-01 + OC-04).

### 6.3 Registry vs stored weather variables

| `weather_variables` (registry) | Persisted @ NASA ingest |
|--------------------------------|-------------------------|
| `rainfall` | `rainfall_mm` |
| `humidity` | `relative_humidity_pct` |
| `acreage` | **Not ingested** (non-IMD source) |

Weather agent: **PARTIAL** on persistence (SI-02 closed for dev tier); **BLOCKED** for production-grade IMD departure/category (WS-01, WS-04).

---

## 7. Signal Readiness — Gap Matrix

Consolidates [SIGNAL_INPUT_READINESS.md](./SIGNAL_INPUT_READINESS.md) with PI6 observation state.

| Agent | Required? | Observation state @ PI6 | Readiness |
|-------|-----------|-------------------------|-----------|
| **Market** | Yes | 0 mandi days @ 5433; proof 8 rows / 2 dates / 2 mandis | **BLOCKED** (history + quality) |
| **Futures** | Yes | 0; DS-001 open | **BLOCKED** |
| **Weather** | Optional | 5,620 NASA rows, 36-mo dense | **PARTIAL** (tier-2 source; no IMD) |
| **Policy** | Optional | No MSP INR; no CCI/PIB; no spot series @ 5433 | **BLOCKED** |

| Gap | Description | Priority |
|-----|-------------|----------|
| **OC-01** | Execute Agmarknet backfill + daily production on 4 mandis | **P0** |
| **OC-02** | `data_quality_snapshot` per refresh | **P0** |
| **OC-03** | DS-001 futures + `msp_inr_quintal` seed/process | **P0** (orchestration) |
| **OC-04** | Align weather/market calendars; document mandi↔region rollup | **P1** |
| **OC-05** | Arrival channel depth Oct–Mar (G6) | **P1** |
| **OC-06** | Apply `0010` partition migration before large price backfill | **P1** |
| **OC-07** | IMD PRIMARY after WS-01 | **P2** (production weather tier) |

---

## 8. Recommended Actions (Research Only)

| Order | Action | Unblocks |
|-------|--------|----------|
| 1 | Run `agmarknet_backfill.py` live or fixture-at-scale on @ 5433; refresh `HISTORICAL_BACKFILL_REPORT` via `--stats --write-report` | OC-01, Market/Policy spot |
| 2 | Wire ingest → `data_quality_snapshot` (lag hours, feed flags) | OC-02 |
| 3 | Close DS-001; add `msp_inr_quintal` to active registry | OC-03, strict MI |
| 4 | Re-run `observation_population_proof.py` or document DB reset policy so proof + weather coexist | Consistent Track F metrics |
| 5 | `alembic upgrade head` → `0010` before multi-year price load | OC-06 |
| 6 | Extend coverage doc after backfill: mandi × month heatmap, `% days reporting` | Track F dashboard inputs |

**Do not** treat PI6 Weather ingest alone as belt **signal readiness** — without mandi price/arrival on the same calendar, MI remains **non-production**.

---

## 9. Live DB Snapshot (@ 5433, 2026-06-04)

| Check | Result |
|-------|--------|
| `alembic_version` | `0009_weather_observations` |
| `market` count | **4** (all Telangana cotton mandis) |
| `price_observation` (cotton, `agmarknet`) | **0** |
| `arrival_observation` (cotton) | **0** |
| `weather_observation` (cotton, `nasa_power`) | **5,620** |
| `data_quality_snapshot` | **0** |
| Weather date span | `2023-05-01` … `2026-05-31` |
| Weather regions | 5 × 1,124 days |

*Note:* PI5 report counts (8 Agmarknet rows) reflect a prior proof run; current @ 5433 retains **weather-only** load (Track D). Reconcile by re-running population proof or full backfill on the same DB.

---

## 10. Traceability

| Section | Sources |
|---------|---------|
| §3 Markets | `cotton.json`, OBSERVATION_POPULATION_REPORT, HISTORICAL_BACKFILL_REPORT, §9 live query |
| §4 Commodity | OBSERVATION_POPULATION_REPORT, cotton mapper constants |
| §5 Dates | HISTORICAL_BACKFILL_REPORT, NASA_POWER_INGESTION_REPORT, §9 |
| §6 Alignment | `cotton.json` regions/markets, WEATHER_DATA_STRATEGY_V1 |
| §7 Signals | SIGNAL_INPUT_READINESS, SIGNAL_ENGINE_V1 |
| §9 Live | SQLAlchemy @ `127.0.0.1:5433/krishinetra` |

---

*End of Observation Coverage Analysis — PI6 Track F.*
