# Observation Validation Report — PI8 Track A

**Date:** 2026-06-04  
**PI:** PI8 Track A (KDO — observation validation pipeline)  
**Workspace:** `058230e`  
**DB:** `postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra`  
**Window:** `2023-06-01` → `2026-06-03` (1,099 days, 27 belt mandis)  
**Mode:** commit (executed)

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| Commodity / source | `cotton` / `agmarknet` |
| Pending before run (price / arrival) | **60,445** / **1,099** |
| Rows examined | **61,544** |
| Validated | **61,544** |
| Rejected | **0** |
| Markets reporting (post-run) | **18** / **27** |
| `overall_quality_score` (after refresh) | **0.8515** |

**Verdict:** All pending `received` rows in the belt window were promoted to `validated` after field checks. Zero rejections. The full **0.30 anomaly penalty** (capped) was removed. Score lift at current coverage (**18/27** markets) is **0.5515 → 0.8515** (+0.30).

### Track B baseline vs executed corpus

Track B analysis (@ `8792` rows, **2/27** markets) projected **0.315 → 0.615**. Between Track B and execution, the integration DB gained additional belt-market fixture rows (**18/27** reporting). Penalty mechanics are unchanged; score lift remains **+0.30** from validation alone.

### Workflow statuses

| Workflow | DB enum |
|----------|---------|
| draft (pending QA) | `received` |
| validated | `validated` |
| rejected | `rejected` |

### Post-run status distribution

| Table | `received` | `validated` | `rejected` |
|-------|----------|-------------|------------|
| `price_observation` | 0 | **60,445** | 0 |
| `arrival_observation` | 0 | **1,099** | 0 |

---

## 2. Validation checks

| Check | Price | Arrival |
|-------|-------|---------|
| Null required fields | yes | yes |
| Price range (INR/quintal) | yes | — |
| Arrival volume range | — | yes |
| Commodity registry mapping | yes | yes |
| Market registry mapping | yes | yes |
| Date consistency (`observed_at` vs `as_of_date`) | yes | yes |

---

## 3. Run breakdown

### 3.1 Price observations

| Metric | Value |
|--------|-------|
| Examined | 60,445 |
| Validated | 60,445 |
| Rejected | 0 |

### 3.2 Arrival observations

| Metric | Value |
|--------|-------|
| Examined | 1,099 |
| Validated | 1,099 |
| Rejected | 0 |

**Rejection reasons:** *(none)*

---

## 4. DQS impact (anomaly penalty)

Non-`validated` / non-`published` rows count as anomalies in `compute_overall_quality_score` (cap 0.30).

```
anomaly_penalty = min(0.30, anomaly_count / row_count)
row_count       = days_with_data × markets_reporting  →  1,099 × 18 = 19,782
```

| Metric | Before | After |
|--------|--------|-------|
| `anomaly_count` | **61,544** | **0** |
| Anomaly penalty | **0.3000** | **0.0000** |
| `coverage_ratio` | 0.6667 | 0.6667 |
| `completeness_ratio` | 1.0 | 1.0 |
| `overall_quality_score` | **0.5515** | **0.8515** |

**Penalty reduction:** **−0.3000**  
**Score lift:** **+0.3000**

`data_quality_snapshot` refreshed via `DataQualitySnapshotService.record_after_agmarknet_ingest` @ `2026-06-03`.

### Track B projection (2/27 markets, 8,792 rows)

| Metric | Before | After |
|--------|--------|-------|
| `overall_quality_score` | **0.3151** | **0.6151** |

Same **−0.30** penalty removal; lower coverage caps absolute score.

---

## 5. Engineering notes

| Item | Detail |
|------|--------|
| Bulk update perf | `_bulk_set_*_status` switched from composite `(observation_id, as_of_date)` tuple-IN to `observation_id`-only IN (chunk 2,000) — commit time **~33 s** for 61k rows vs >13 min prior |
| Modal dedupe (P1) | **Deferred** — 1,099 Khammam duplicate modals remain; both copies validated cleanly; dedupe is hygiene, not penalty-blocking post-P0 |
| Weather blend | DQS uses Agmarknet-only path in this refresh; weather-weighted blend may adjust composite score separately |

---

## 6. Deliverables

| Artifact | Path |
|----------|------|
| Validation service | `backend/app/services/validation/observation_validation_service.py` |
| Field validators | `backend/app/persistence/validation/agmarknet_observation.py` |
| Batch CLI | `scripts/observation_validate.py` |
| Migration (`rejected`) | `backend/app/persistence/migrations/versions/0011_observation_validation_rejected.py` |
| Track B analysis | `docs/reviews/ANOMALY_ANALYSIS_REPORT.md` |

### Reproduce

```bash
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/observation_validate.py \
    --window-start 2023-06-01 --window-end 2026-06-03 \
    --refresh-snapshot --write-report
```

---

## 7. Return payload

| Field | Value |
|-------|-------|
| **Rows validated** | **61,544** (60,445 price + 1,099 arrival) |
| **New quality score** | **0.8515** |
| **Report path** | `docs/reviews/OBSERVATION_VALIDATION_REPORT.md` |

---

*End of PI8 Track A observation validation report.*
