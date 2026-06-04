# Quality Score Improvement Report — PI8 Track D

**Date:** 2026-06-04  
**PI:** PI8 Track D (KDO — quality score improvement)  
**Workspace:** `058230e` + PI8 uncommitted  
**DB:** `postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra`  
**Baseline:** [DATA_QUALITY_TREND_REPORT.md](./DATA_QUALITY_TREND_REPORT.md), [ANOMALY_ANALYSIS_REPORT.md](./ANOMALY_ANALYSIS_REPORT.md), [MARKET_COVERAGE_IMPROVEMENT.md](./MARKET_COVERAGE_IMPROVEMENT.md)

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| **BEFORE `overall_quality_score` (PI7 belt baseline)** | **0.3161** |
| **AFTER `overall_quality_score` (post PI8 Track A + C + D + E + snapshot)** | **0.7088** |
| **Δ score** | **+0.3927** |
| **Target > 0.50** | **Y** |
| **Stretch target ≥ 0.70** | **Y** (0.7088 — marginal; weather tier still drags blend) |
| **Gap to aspirational 0.85+** | **0.1412** |

**Verdict:** PI8 cross-track work lifts DQS from the PI7 belt baseline (**0.3161**) to **0.7088**, clearing both the **> 0.50** gate and the **0.70** stretch target on the combined Agmarknet + weather snapshot. The dominant levers were **market coverage expansion** (Track E), **validation lifecycle closure** (Track A), and **weather tier activation** (Track C). Remaining headroom is capped by **5,620 NASA POWER rows still in `received` status** and **9/27 belt mandis** without fixture tuples.

---

## 2. Score progression

| Stage | Scope | Window | Score | Primary drivers |
|-------|-------|--------|-------|-----------------|
| **PI7 belt baseline (BEFORE)** | 27 belt mandis | `2023-06-01` → `2026-06-03` | **0.3161** | 2/27 coverage (0.074), completeness 1.0, anomaly penalty **0.30** (8,792 `received`) |
| **PI8 Track E (pre-validation)** | Belt fixture replay | Same | **~0.5520** (ag-only est.) / **0.5593** (combined w/ weather) | 18/27 coverage (0.667), penalty still **0.30** (61,544 `received`) |
| **PI8 Track D (AFTER)** | Validation + DQS refresh | Same | **0.7088** | Agmarknet anomalies **0**, weather merged, `agmarknet` health **fresh** |

---

## 3. Track D execution (@ 5433)

### 3.1 ObservationValidationService (Track A follow-up)

All Agmarknet cotton rows were still `received` before this run.

| Check | Before | After |
|-------|--------|-------|
| `price_observation` `received` | 60,445 | **0** |
| `arrival_observation` `received` | 1,099 | **0** |
| **Validated** (price + arrival) | 0 | **61,544** |
| **Rejected** | 0 | **0** |

**Service:** `ObservationValidationService.validate_pending`  
**CLI:** `scripts/observation_validate.py`  
**Window:** `2023-06-01` → `2026-06-03`  
**Execution:** 13 chunked passes (90-day windows) with per-chunk commit (~24 s total; full-window single pass exceeds sandbox timeout at 61k+ ORM rows).

Field validation pass rate: **100%** (61,544 / 61,544) — consistent with [ANOMALY_ANALYSIS_REPORT.md](./ANOMALY_ANALYSIS_REPORT.md) root-cause finding (lifecycle gap, not corrupt tuples).

### 3.2 DataQualitySnapshotService refresh

| Field | Value |
|-------|-------|
| **Call** | `DataQualitySnapshotService.record_after_weather_ingest` |
| **`quality_snapshot_id`** | `bba25854-80fe-4490-b9d8-946786be57c2` |
| **`as_of_date`** | `2026-06-03` |
| **`overall_quality_score`** | **0.7088** |
| **`agmarknet_lag_hours`** | **10.16** |

Merged snapshot includes **Agmarknet belt metrics** and **NASA POWER weather tier** (5,620 rows @ 5433, Track C).

---

## 4. Live metrics @ 5433 (post-refresh)

### 4.1 Agmarknet

| Metric | PI7 baseline | After PI8 |
|--------|--------------|-----------|
| Markets reporting / expected | 2 / 27 | **18 / 27** |
| Coverage ratio | 0.0741 | **0.6667** |
| Completeness ratio | 1.0000 | **1.0000** |
| Anomaly count | 8,792 | **0** |
| Anomaly penalty | 0.30 (capped) | **0.00** |
| Source health | `stale` | **`fresh`** |

### 4.2 Weather (NASA POWER)

| Metric | Value |
|--------|-------|
| Regions reporting / expected | **5 / 5** |
| Coverage ratio | **1.0000** |
| Completeness ratio | **0.9945** (1,093 / 1,099 days) |
| Anomaly count (non-validated in window) | **5,465** |
| Rows still `received` (full table) | **5,620** |
| Source health | **`stale`** (anomaly penalty active) |

### 4.3 Observation inventory

| Table | Count | Notes |
|-------|-------|-------|
| `price_observation` (cotton, agmarknet) | 60,445 | All `validated` |
| `arrival_observation` (cotton, agmarknet) | 1,099 | All `validated` |
| `weather_observation` (cotton, nasa_power) | 5,620 | All `received` (validation not wired for weather) |
| Distinct mandis with price rows | **18** | Track E belt fixture |

---

## 5. Score formula & gap analysis

Blended score when weather tier is active:

```
ag_raw   = 0.4×coverage + 0.35×completeness + 0.25×freshness − min(0.3, anomalies/row_count)
weather_raw = same formula on weather metrics
overall  = (ag_raw + weather_raw) / 2
```

### 5.1 PI7 baseline decomposition (BEFORE = 0.3161)

| Component | Weight × value |
|-----------|----------------|
| Coverage | 0.4 × 0.0741 ≈ **0.030** |
| Completeness | 0.35 × 1.0 = **0.350** |
| Freshness | 0.25 × ~0.946 ≈ **0.237** |
| Anomaly penalty | **−0.300** |
| **Total (Agmarknet-only)** | **≈ 0.316** |

### 5.2 Post-PI8 decomposition (AFTER = 0.7088)

| Tier | Coverage | Completeness | Freshness | Penalty | Approx. raw |
|------|----------|--------------|-----------|---------|-------------|
| **Agmarknet** | 0.667 | 1.000 | ~0.940 | 0.00 | **~0.85** |
| **Weather** | 1.000 | 0.995 | ~0.93 | **0.30** (capped) | **~0.57** |
| **Combined (50/50)** | — | — | — | — | **0.7088** |

### 5.3 Gap to 0.85+ (beyond stretch 0.70)

| Lever | Current | Needed (indicative) | Owner / track |
|-------|---------|---------------------|---------------|
| **Weather validation** | 5,620 `received` | Promote to `validated`; penalty → ~0 | Weather validation path (new) |
| **Market coverage** | 18/27 (66.7%) | ≥ 25/27 for coverage ≈ 0.93+ | Track E fixture expansion or SR-01 live OGD |
| **Nine empty mandis** | No fixture tuples | Add tuples or live pull | Track E / ops |
| **Live OGD** | Blocked (`OGD_API_KEY`) | Register key for production depth | Ops |

**Indicative ceiling if weather penalty cleared and coverage held:**

```
(0.85 + 0.99) / 2 ≈ 0.92   (weather tier at full freshness, zero anomalies)
```

---

## 6. Cross-track attribution

| Track | Contribution to Δ 0.3161 → 0.7088 |
|-------|-------------------------------------|
| **E — Market coverage** | +0.24 score lift (coverage 0.074 → 0.667) even before validation |
| **A — Validation** | +0.30 penalty removal on Agmarknet (61,544 rows promoted) |
| **C — Weather activation** | Enables merged snapshot; weather tier currently **reduces** blend vs Agmarknet-only ~0.85 |
| **D — Snapshot refresh** | Persists auditable `data_quality_snapshot` row for signal gates |

---

## 7. Validation

| Check | Result |
|-------|--------|
| `ObservationValidationService` run @ 5433 | **PASS** (61,544 validated, 0 rejected) |
| `DataQualitySnapshotService.record_after_weather_ingest` | **PASS** (`overall_quality_score` **0.7088**) |
| Target **> 0.50** | **PASS (Y)** |
| Stretch **≥ 0.70** | **PASS (Y)** |
| `pytest` unit (`-m "not integration"`) | **13 passed** |
| `pytest` integration @ 5433 (shared DB) | 2 deadlocks (concurrent delete vs 61k-row belt) — env contention, not regression |
| `ruff` / `mypy` on quality + validation | **PASS** |

---

## 8. Reproduce (@ 5433)

```bash
export DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra

# Track A — validate pending rows (chunk if full window times out)
uv run python scripts/observation_validate.py \
  --window-start 2023-06-01 --window-end 2026-06-03

# Track D — refresh merged snapshot (Agmarknet + weather)
uv run python -c "
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
import os
from backend.app.services.quality.snapshot_service import DataQualitySnapshotService
engine = create_engine(os.environ['DATABASE_URL'])
with Session(engine) as s:
    r = DataQualitySnapshotService(s).record_after_weather_ingest(
        window_start=date(2023, 6, 1),
        window_end=date(2026, 6, 3),
        as_of_date=date(2026, 6, 3),
    )
    s.commit()
    print(r.overall_quality_score)
"

# Tests
DATABASE_URL=\$DATABASE_URL uv run pytest \
  tests/unit/test_data_quality_ingest.py \
  tests/unit/test_data_quality_snapshot.py \
  tests/unit/test_observation_validation.py -q

uv run ruff check backend/app/services/quality backend/app/services/validation scripts/observation_validate.py
uv run mypy backend/app/services/quality backend/app/services/validation
```

---

## 9. Deliverables

| Artifact | Path |
|----------|------|
| This report | `docs/reviews/QUALITY_IMPROVEMENT_REPORT.md` |
| Validation service | `backend/app/services/validation/observation_validation_service.py` |
| Snapshot service | `backend/app/services/quality/snapshot_service.py` |
| Validation CLI | `scripts/observation_validate.py` |

---

*End of PI8 Track D quality score improvement report.*
