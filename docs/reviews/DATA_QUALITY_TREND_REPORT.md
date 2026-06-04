# Data Quality Trend Report — PI7 Track E

**Date:** 2026-06-04  
**PI:** PI7 Track E (KDO — data quality improvement & trend)  
**DB:** `postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra` @ workspace `f72a1fb` + PI7 uncommitted  
**Service:** `DataQualitySnapshotService` (`backend/app/services/quality/snapshot_service.py`)

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| Snapshot refreshed @ 5433? | **Yes** — `DataQualitySnapshotService.record_after_agmarknet_backfill` (36-mo belt window) + `--stats` path now also refreshes DQS |
| **Current `overall_quality_score` (belt, 36-mo)** | **0.3161** |
| PI6 baseline (30-day proof ingest) | **0.0617** |
| PI7 fixture milestone (TG4, sparse fixture rows) | **0.1374** |
| Signal / ops target | **0.70** |
| **Gap to target** | **0.3839** (`0.70 − 0.3161`) |
| Live Agmarknet | **BLOCKED** — `OGD_API_KEY` not registered |

**Verdict:** Engineering path for DQS is **PASS**; depth and market breadth remain **YELLOW**. Calendar completeness is strong (1,099/1,099 days with price rows in window), but **market coverage** (2/27 reporting on latest date) and **anomaly penalty** (8,792 non-validated rows) cap the score well below the 0.70 target.

---

## 2. Quality score progression

| Stage | Scope | Window | Score | Primary drivers |
|-------|-------|--------|-------|-----------------|
| **PI6 baseline** | TG4 mandis | 30 days @ `2026-06-04` | **0.0617** | 1/4 markets, 1/30 days, 3 anomalies ([DATA_QUALITY_REPORT.md](./DATA_QUALITY_REPORT.md)) |
| **PI7 fixture** | TG4 mandis | 36 mo `2023-06-01` → `2026-06-03` | **0.1374** | 2/4 markets, 3/1,099 days, ~24 rows ([E03_S02_COMPLETION_REPORT.md](./E03_S02_COMPLETION_REPORT.md)) |
| **PI7 belt (current @ 5433)** | 27 seeded belt mandis | Same 36-mo window | **0.3161** | 2/27 markets on latest date, **1.0** completeness, anomaly penalty **0.30** (capped) |
| **TG4 lens (same DB)** | 4 TG primaries | Same 36-mo window | **0.4864** | 2/4 coverage; completeness 1.0; same anomaly pool |
| **Target** | Belt + weather tiers healthy | 36-mo + daily refresh | **≥ 0.70** | Requires SR-01 live backfill, validation hygiene, weather tier loaded |

**Trend:** Score rose from proof-scale daily ingest (**0.0617**) through partial fixture load (**0.1374**) to the current belt view (**0.3161**) as calendar days filled in, but **widening expected markets from 4 → 27** lowered coverage ratio (0.25 → 0.074) and prevented a monotonic climb toward 0.70.

---

## 3. Live metrics @ 5433 (2026-06-04 refresh)

**Snapshot ID:** `e4236df1-5e0e-4568-bb91-0303d289a0d8`  
**`as_of_date`:** `2026-06-03`  
**`overall_quality_score`:** **0.3161**  
**`agmarknet_lag_hours`:** **9.12**

### 3.1 Observation inventory

| Table | Count | Notes |
|-------|-------|-------|
| `price_observation` (cotton) | **7,693** | Agmarknet source |
| `arrival_observation` (cotton) | **1,099** | |
| `weather_observation` (cotton) | **0** | NASA POWER backfill not present on this DB (reported 5,620 rows in PI7 Track D docs) |
| `market` (cotton seed) | **27** | PI7 belt seed ([MARKET_COVERAGE_REPORT.md](./MARKET_COVERAGE_REPORT.md)) |
| Distinct mandis with any price row | **2** | `mkt_tg_khammam_apmc`, `mkt_tg_warangal` (in-window) |
| Price `as_of_date` span | `2023-06-01` → `2026-06-03` | 1,099 distinct days |

### 3.2 Coverage

| Metric | Value |
|--------|-------|
| Markets reporting / expected (belt) | **2** / **27** |
| Coverage ratio | **0.0741** |
| Markets reporting / expected (TG4) | **2** / **4** |
| TG4 coverage ratio | **0.5000** |

### 3.3 Freshness

| Metric | Value |
|--------|-------|
| Latest `as_of_date` | `2026-06-03` |
| `agmarknet_lag_hours` | **9.12** |
| Freshness component (168h decay) | ~**0.946** |
| `agmarknet` source health | **`stale`** (coverage &lt; 0.5) |

### 3.4 Completeness

| Metric | Value |
|--------|-------|
| Window days | **1,099** |
| Days with price data | **1,099** |
| Completeness ratio | **1.0000** |

### 3.5 Anomalies

| Metric | Value |
|--------|-------|
| Non-validated rows in window | **8,792** |
| Anomaly penalty (cap 0.30) | **0.30** (`min(0.3, anomalies/row_count)`) |
| Effective row_count proxy | 2,198 (`days × markets_reporting`) |

### 3.6 Weather tier (optional merge)

| Metric | Value |
|--------|-------|
| Regions reporting / expected | **0** / **5** |
| `weather` source health | **`missing`** |
| Combined score if empty weather merged | ~~0.2831~~ — **fixed:** empty weather tier no longer dilutes Agmarknet score (`regions_reporting <= 0` → Agmarknet-only) |

---

## 4. Score formula & gap analysis (target 0.70)

Blended score (Agmarknet-only when weather empty):

```
raw = 0.4×coverage + 0.35×completeness + 0.25×freshness − anomaly_penalty
anomaly_penalty = min(0.3, anomaly_count / row_count)
```

**Current belt decomposition (approx.):**

| Component | Weight × value |
|-----------|----------------|
| Coverage | 0.4 × 0.0741 ≈ **0.030** |
| Completeness | 0.35 × 1.0 = **0.350** |
| Freshness | 0.25 × 0.946 ≈ **0.237** |
| Anomaly penalty | **−0.300** |
| **Total** | **≈ 0.316** |

### 4.1 What must change to reach 0.70

| Lever | Current | Needed (indicative) | Owner |
|-------|---------|---------------------|-------|
| **Market coverage** | 2/27 (7.4%) | **≥ ~25/27** reporting on latest date (coverage ≈ 0.93+) | SR-01 live OGD backfill + daily ingest |
| **Anomaly / validation** | 8,792 non-validated | Penalty &lt; 0.05 (validated pipeline or row_count growth) | E-03 validation / publish path |
| **Weather tier** | 0 rows | 5/5 regions, completeness ≈ 1.0; then 50/50 blend with healthy Agmarknet | Track D `nasa_power_ingest.py` on @ 5433 |
| **Live OGD** | Blocked | Register `OGD_API_KEY` | Ops |

**Illustrative clean state (both tiers healthy):** coverage 1.0, completeness 1.0, lag 2h, 0 anomalies → per-tier score **~0.997**; combined average **~0.997**.

With **current** anomaly load, coverage alone cannot reach 0.70 even at completeness 1.0: maximum raw before penalty ≈ **0.616**, minus 0.30 penalty ≈ **0.316** (matches observed).

---

## 5. Ingest → snapshot wiring

| Trigger | Call | Status |
|---------|------|--------|
| Agmarknet daily ingest | `record_after_agmarknet_ingest` | Wired (`pipeline.py`) |
| Agmarknet backfill | `record_after_agmarknet_backfill` | Wired (`backfill.py`) |
| NASA POWER ingest | `record_after_weather_ingest` | Wired (`weather/pipeline.py`) |
| `agmarknet_backfill.py --stats` | `record_after_agmarknet_backfill` + commit | **Added PI7** — refreshes DQS after stats-only runs |
| Empty weather tier | Agmarknet-only combined score | **Fixed PI7** — avoids false downgrade when `weather_observation` empty |

---

## 6. Test gate

```bash
uv run ruff check backend/app/services/quality/ scripts/agmarknet_backfill.py
uv run mypy backend/app/services/quality/ scripts/agmarknet_backfill.py
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run pytest tests/unit/test_data_quality_ingest.py \
    tests/unit/test_data_quality_snapshot.py -q
```

---

## 7. Return payload (parent agent)

| Field | Value |
|-------|-------|
| **Current quality score** | **0.3161** |
| **Report path** | `docs/reviews/DATA_QUALITY_TREND_REPORT.md` |
| **Gap to 0.70 target** | **0.3839** |

---

## 8. References

| Doc | Role |
|-----|------|
| [DATA_QUALITY_REPORT.md](./DATA_QUALITY_REPORT.md) | PI6 Track E baseline (0.0617) |
| [E03_S02_COMPLETION_REPORT.md](./E03_S02_COMPLETION_REPORT.md) | PI7 fixture score (0.1374) |
| [MARKET_COVERAGE_REPORT.md](./MARKET_COVERAGE_REPORT.md) | 27-market belt seed |
| [NASA_POWER_BACKFILL_REPORT.md](./NASA_POWER_BACKFILL_REPORT.md) | Weather tier target (5,620 rows) |
| [SIGNAL_READINESS_ASSESSMENT.md](../research/SIGNAL_READINESS_ASSESSMENT.md) | SR-01 / signal depth gates |

---

*End of PI7 Track E data quality trend report.*
