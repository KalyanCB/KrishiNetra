# Data Quality Snapshot Report — PI6 Track E

**Date:** 2026-06-04
**PI:** PI6 Track E (KDO — `data_quality_snapshot` ingest wiring)
**Status:** Snapshot writer wired to Agmarknet + optional weather ingest

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Snapshot persisted? | **Yes** — `quality_snapshot_id` `e0611fb2-f7e5-4317-9d1f-92cf49ae4706` |
| Active `registry_id` (FK) | `7332e4b7-383e-4d22-b3dd-759dbdca89c1` |
| `as_of_date` | `2026-06-04` |
| `overall_quality_score` | **0.0617** |
| `agmarknet_lag_hours` | **0.0** |

---

## 2. Agmarknet metrics

| Metric | Value |
|--------|-------|
| Markets reporting / expected | **1** / **4** |
| Coverage ratio | **0.2500** |
| Days with data / window | **1** / **30** |
| Completeness ratio | **0.0333** |
| Latest `as_of_date` | `2026-06-04` |
| Anomaly count (non-validated) | **3** |
| Source health | `stale` |

---

## 3. Ingest wiring

| Trigger | Service call | `as_of_date` |
|---------|--------------|--------------|
| Agmarknet daily ingest | `DataQualitySnapshotService.record_after_agmarknet_ingest` | Max trade date in batch (inserted rows, else batch drafts) |
| Agmarknet backfill | `record_after_agmarknet_backfill(window_start, window_end)` | Window end |
| NASA POWER ingest (optional) | `record_after_weather_ingest` | Ingest end date; merges `weather` into `source_health` |

**FK:** `registry_id` from `RegistryService.get_active_config("cotton")`.

---

## 4. Tests (@ 5433)

| Module | Unit (no DB) | Integration (`DATABASE_URL`) | Total |
|--------|--------------|------------------------------|-------|
| `test_data_quality_ingest.py` | 5 | 3 | **8** |
| `test_data_quality_snapshot.py` (S08) | 2 | 2 | 4 |

```bash
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  .venv/bin/pytest tests/unit/test_data_quality_ingest.py -q
```

---

## 5. Deliverables

| Artifact | Path |
|----------|------|
| Quality service | `backend/app/services/quality/snapshot_service.py` |
| Metrics helpers | `backend/app/services/quality/metrics.py` |
| Repository upsert | `backend/app/persistence/repositories/quality.py` |
| Unit tests | `tests/unit/test_data_quality_ingest.py` |

---

## 6. Sample `source_health` fields

```json
{
  "agmarknet": "stale",
  "agmarknet_detail": {
    "markets_expected": 4,
    "markets_reporting": 1,
    "coverage_ratio": 0.25,
    "window_days": 30,
    "days_with_data": 1,
    "completeness_ratio": 0.0333,
    "latest_as_of_date": "2026-06-04",
    "anomaly_count": 3
  }
}
```
