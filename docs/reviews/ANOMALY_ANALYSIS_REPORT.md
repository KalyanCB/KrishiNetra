# Anomaly Analysis Report — PI8 Track B

**Date:** 2026-06-04  
**PI:** PI8 Track B (KDO — anomaly reduction analysis)  
**Workspace:** `058230e`  
**DB:** `postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra`  
**Window:** `2023-06-01` → `2026-06-03` (1,099 days, 27 belt mandis)

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| Observation rows in window | **8,792** (7,693 price + 1,099 arrival) |
| DQS anomaly count (non-`validated` / non-`published`) | **8,792** (100%) |
| Anomaly penalty (cap 0.30) | **0.30** (maxed) |
| Markets reporting / expected | **2** / **27** |
| `overall_quality_score` (belt) | **0.3151** |
| Field validation pass rate (dry-run) | **100%** (8,792 / 8,792) |

**Verdict:** Every row in the belt window counts as a DQS anomaly because ingest leaves `validation_status = received` and **Track A validation has not been run post-backfill**. Row-level field checks pass; the penalty is almost entirely a **lifecycle status gap**, not corrupt data. A secondary **duplicate-modal** pattern (1,099 rows) stems from fixture ingest design and does not block validation but should be fixed in dedupe/mapping.

---

## 2. Classification breakdown

DQS treats any row with `validation_status ∉ {validated, published}` as an anomaly (`snapshot_service._count_anomalies`). Track B additionally classifies **data-quality root causes** using `agmarknet_observation.py` validators and SQL audits.

### 2.1 Primary DQS anomaly driver

| Category | Rows | % of total | DQS penalty impact |
|----------|------|------------|-------------------|
| **Non-validated status** (`received`) | **8,792** | **100%** | **−0.30** (capped) |

All 8,792 rows are `received`. None are `validated`, `published`, `rejected`, or `superseded`.

### 2.2 Data-quality root-cause taxonomy

| Category | Rows affected | % of total | Persists as DQS anomaly? | Notes |
|----------|---------------|------------|--------------------------|-------|
| **Missing required fields** | **0** | 0% | No | DB `NOT NULL` + ingest mapper enforce market, commodity, value/volume, dates |
| **Missing optional fields** | **1,099** | 12.5% | No* | `quality_grade IS NULL` on Khammam duplicate modal rows only |
| **Mapping failures (persisted)** | **0** | 0% | No | All rows map to seeded belt `market_id` + `cotton` |
| **Mapping failures (ingest drop)** | ~**5,495**/day×Maize | — | N/A | Maize fixture row excluded by `EXCLUDED_COMMODITY_LABELS`; 25/27 mandis have zero OGD rows (fixture TG-only) |
| **Duplicate observations** | **1,099** extra | 12.5% redundant | Yes† | Khammam `modal` duplicated once per calendar day |
| **Stale observations** | **0** | 0% | No | `observed_at` = 18:30 UTC on `as_of_date` for all rows; passes `MAX_OBSERVED_DATE_LAG_DAYS = 1` |

\*Optional nulls do not fail Track A field validation.  
†Duplicates remain separate anomaly rows until deduped or superseded; both copies would validate cleanly today.

### 2.3 Validation status distribution

| Table | `received` | `validated` | `published` | `rejected` |
|-------|----------|-------------|-------------|------------|
| `price_observation` | 7,693 | 0 | 0 | 0 |
| `arrival_observation` | 1,099 | 0 | 0 | 0 |

### 2.4 Duplicate observation detail

| Market | `price_type` | Days with dup key | Extra rows |
|--------|--------------|-------------------|------------|
| `mkt_tg_khammam_apmc` | `modal` | 1,099 | **1,099** |
| *all others* | — | 0 | 0 |

**Root cause:** Fixture `ogd_telangana_sample.json` contains two Khammam cotton records for the same trade date — one full price row (`Cotton\|FAQ`) and one arrival row with `modal_price` only (`quality_grade = NULL`). Dedupe key includes `quality_grade` (`dedupe.price_business_key`), so both modals insert.

Sample (`2023-06-01`, Khammam modal):

| `value` | `quality_grade` |
|---------|-----------------|
| 10500 | `Cotton\|FAQ` |
| 10500 | `NULL` |

### 2.5 Price row shape

| `price_type` | Count | Per-day avg (÷1,099) |
|--------------|-------|----------------------|
| `modal` | 3,297 | 3.0 |
| `min` | 2,198 | 2.0 |
| `max` | 2,198 | 2.0 |

Expected: 3 types × 2 markets = 6/day → 6,594; actual 7,693 includes 1,099 duplicate modals.

### 2.6 Market distribution

| `market_id` | Rows | Distinct dates |
|-------------|------|----------------|
| `mkt_tg_khammam_apmc` | 5,495 | 1,099 |
| `mkt_tg_warangal` | 3,297 | 1,099 |
| *25 belt mandis* | 0 | 0 |

Warangal rows originate from fixture `Kapas` label (mapped via `COTTON_COMMODITY_LABELS`). This is **intentional cotton mapping**, not a persisted mapping failure.

---

## 3. DQS penalty mechanics

```
anomaly_penalty = min(0.30, anomaly_count / row_count)
row_count       = days_with_data × markets_reporting  →  1,099 × 2 = 2,198
```

| Metric | Current | After Track A validation |
|--------|---------|--------------------------|
| `anomaly_count` | 8,792 | **0** (dry-run: 0 rejected) |
| `anomaly_penalty` | **0.3000** | **0.0000** |
| `overall_quality_score` | **0.3151** | **0.6151** |

Coverage (2/27) still caps score below the **0.70** target even with zero anomalies. Validation removes the **0.30 ceiling** and is the largest single lever available without live OGD backfill.

---

## 4. Track A validation pipeline — dry-run @ 5433

Executed via `ObservationValidationService.validate_pending(dry_run=True)`:

| Metric | Price | Arrival | Total |
|--------|-------|---------|-------|
| Pending (`received`) | 7,693 | 1,099 | 8,792 |
| Examined | 7,693 | 1,099 | 8,792 |
| Would validate | 7,693 | 1,099 | **8,792** |
| Would reject | 0 | 0 | **0** |
| Rejection reasons | — | — | *(none)* |

Infrastructure already present:

| Artifact | Path |
|----------|------|
| Field validators | `backend/app/persistence/validation/agmarknet_observation.py` |
| Batch service | `backend/app/services/validation/observation_validation_service.py` |
| CLI | `scripts/observation_validate.py` |
| Enum migration (`rejected`) | `0011_observation_rejected` ✓ applied @ 5433 |

---

## 5. Actionable fixes for Track A (priority order)

### P0 — Run post-ingest validation (largest penalty reduction)

**Fix:** Call `ObservationValidationService.validate_pending()` after Agmarknet backfill/daily ingest; commit; refresh DQS snapshot.

```bash
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/observation_validate.py \
    --window-start 2023-06-01 --window-end 2026-06-03 --refresh-snapshot
```

**Wire in code:** Add hook in `AgmarknetBackfillPipeline` and `AgmarknetIngestPipeline._persist_mapped` (after commit) mirroring existing `record_after_agmarknet_*` snapshot calls.

| Impact | Value |
|--------|-------|
| Penalty reduction | **−0.30** |
| Score lift (current coverage) | **0.315 → 0.615** |
| Rows promoted | **8,792 → validated** |

### P1 — Tighten modal dedupe for arrival-only OGD rows

**Fix (mapper):** In `_map_prices`, skip `modal` when the source row is arrival-primary (has `arrival_tonnes`, no min/max) **or** merge arrival modal into existing price tuple.

**Fix (dedupe):** Change `price_business_key` to `(market_id, as_of_date, source, price_type)` — drop `quality_grade` from uniqueness — so duplicate modals with identical economics collapse.

| Impact | Value |
|--------|-------|
| Rows removed | **−1,099** price duplicates |
| Residual anomaly risk | Lower row cardinality; cleaner signal inputs |

### P2 — Optional quality_grade backfill

**Fix:** When variety/grade absent on arrival-only rows, inherit grade from same-day full price row or set sentinel `unknown`.

| Impact | 1,099 soft nulls → populated; no DQS change until P0 |

### P3 — Ingest-level mapping (coverage, not anomaly rows)

**Fix:** Live OGD backfill across 5 states (`load_backfill_ogd_states`) with `OGD_API_KEY`; audit market spellings per [MARKET_COVERAGE_REPORT.md](./MARKET_COVERAGE_REPORT.md).

| Impact | Raises **coverage_ratio** (currently 0.074); required for **> 0.70** score |

### P4 — CLI robustness

**Fix:** `observation_validate.py` passes invalid `commodity_id` kwarg to `compute_agmarknet_metrics` — repair before ops automation.

---

## 6. Top fix for penalty reduction

> **Run the existing Track A batch validator post-backfill** to promote all 8,792 field-clean `received` rows to `validated`.

- **Why:** 100% of DQS anomalies are lifecycle status only; dry-run shows 0 rejections.
- **Penalty removed:** **0.30** (full cap).
- **Score gain:** **+0.30** (0.315 → 0.615 at current 2/27 coverage).
- **Effort:** CLI one-liner + ingest hook (~10 lines in backfill/pipeline).

Duplicate-modal cleanup (P1) improves data hygiene but does **not** reduce penalty while rows remain `received`; validation (P0) is strictly dominant.

---

## 7. Analysis tooling

| Artifact | Path |
|----------|------|
| **This report** | `docs/reviews/ANOMALY_ANALYSIS_REPORT.md` |
| Classification script | `scripts/anomaly_analysis.py` |
| Track A validator | `scripts/observation_validate.py` |

```bash
# Reproduce classification @ 5433
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/anomaly_analysis.py --json

# Dry-run validation counts
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/observation_validate.py --dry-run \
    --window-start 2023-06-01 --window-end 2026-06-03
```

---

## 8. Return payload (parent agent)

| Field | Value |
|-------|-------|
| **Classification breakdown** | non-validated **100%**; missing required **0%**; optional null grade **12.5%**; mapping failures (persisted) **0%**; duplicates **12.5%** (1,099); stale **0%** |
| **Top fix** | Post-ingest `ObservationValidationService.validate_pending()` → **−0.30 penalty**, score **0.315 → 0.615** |
| **Report path** | `docs/reviews/ANOMALY_ANALYSIS_REPORT.md` |

---

## 9. References

| Doc | Role |
|-----|------|
| [DATA_QUALITY_TREND_REPORT.md](./DATA_QUALITY_TREND_REPORT.md) | DQS formula, 8,792 anomaly baseline |
| [E03_S02_COMPLETION_REPORT.md](./E03_S02_COMPLETION_REPORT.md) | Fixture backfill counts |
| [MARKET_COVERAGE_REPORT.md](./MARKET_COVERAGE_REPORT.md) | 27-market belt seed |

---

*End of PI8 Track B anomaly analysis report.*
