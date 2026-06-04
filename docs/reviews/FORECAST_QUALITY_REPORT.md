# Forecast Quality Report — PI11 Track D

**Date:** 2026-06-04
**PI:** PI11 Track D (KDO — `ForecastQualityService`)
**Status:** Backtest KPIs from evaluation pairs (no user-facing forecast API)

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Commodity / `as_of_date` | `cotton` / `2025-12-01` |
| Active `registry_id` (FK) | `a1b2c3d4-e5f6-4789-a012-3456789abcde` |
| `model_version` | `v0.1.0-pi11` |
| Assessment source | `backtest` |
| Total evaluation pairs | **3** |
| Forecast quality service operational? | **Yes** |

---

## 2. KPIs by horizon (TDS-000)

| Horizon (days) | n | MAE | RMSE | MAPE (%) | Coverage |
|----------------|---|-----|------|----------|----------|
| **30** | **1** | **100.0000** | **100.0000** | **1.6393** | **1.0000** |
| **60** | **1** | **200.0000** | **200.0000** | **3.1746** | **1.0000** |
| **90** | **1** | **300.0000** | **300.0000** | **4.6154** | **1.0000** |

Coverage = fraction of realized prices inside `[band_low, band_high]` (TDS-011 §5.1 interval reliability). MAPE excludes near-zero actuals.

---

## 3. Deliverables

| Artifact | Path |
|----------|------|
| Forecast quality service | `backend/app/services/forecast/quality/service.py` |
| Metrics helpers | `backend/app/services/forecast/quality/metrics.py` |
| Persistence table | `forecast_quality_metric` |
| Migration | `backend/app/persistence/migrations/versions/0015_forecast_quality_metric.py` |
| Unit tests | `tests/unit/test_forecast_quality.py` |

---

## 4. Sample metrics payload

```json
{
  "commodity_id": "cotton",
  "as_of_date": "2025-12-01",
  "registry_id": "a1b2c3d4-e5f6-4789-a012-3456789abcde",
  "model_version": "v0.1.0-pi11",
  "assessment_source": "backtest",
  "sample_count_total": 3,
  "by_horizon": {
    "30": {
      "horizon_days": 30,
      "sample_count": 1,
      "mae": 100.0,
      "rmse": 100.0,
      "mape": 1.6393,
      "coverage": 1.0
    },
    "60": {
      "horizon_days": 60,
      "sample_count": 1,
      "mae": 200.0,
      "rmse": 200.0,
      "mape": 3.1746,
      "coverage": 1.0
    },
    "90": {
      "horizon_days": 90,
      "sample_count": 1,
      "mae": 300.0,
      "rmse": 300.0,
      "mape": 4.6154,
      "coverage": 1.0
    }
  }
}
```

## 5. Quality gates

| Gate | Result |
|------|--------|
| pytest tests/unit/test_forecast_quality.py | **8 passed**, 1 skipped (integration) |
| ruff check (quality modules) | **Pass** |
| mypy (quality modules) | **Pass** |
| User-facing forecast API | **None** (service-only) |

---

## 6. Reference return values (PI11 Track D)

| Field | Value |
|-------|-------|
| Service path | backend/app/services/forecast/quality/service.py |
| Persistence table | forecast_quality_metric |
| Migration head (post-0015) | 0015_forecast_quality_metric |
| Unit test count | **8** (+ 1 integration when DATABASE_URL set) |
| Report path | docs/reviews/FORECAST_QUALITY_REPORT.md |

*End of PI11 Track D forecast quality report.*
