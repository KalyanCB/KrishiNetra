# Feature Importance Report — PI11 Track C

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI11 Track C (KDO — RF baseline feature importance) |
| **Workspace** | `2fb4e5b` |
| **Mode** | `fixture` |
| **Horizon** | **30d** (`target_log_return`) |
| **Commodity** | `cotton` |
| **Window** | `2025-09-19` → `2026-01-16` |
| **Panel rows** | **120** |
| **Feature columns** | **18** |
| **Model source** | `fitted_baseline_feature_mismatch` |
| **RF config** | `n_estimators=50`, `random_state=42` (Track A) |

**Method:** `RandomForestRegressor` feature importances (Gini). Features grouped by lineage prefix (`market.*`, `weather.*`, `futures.*`) aligned with `feature_lineage.agents`.

---

## 1. Executive summary

| Lineage group | Aggregate importance | Top feature |
|---------------|---------------------|-------------|
| **Market** | `0.377019` | `market.magnitude` |
| **Futures** | `0.366655` | `futures.components.basis_futures_spot` |
| **Weather** | `0.256326` | `weather.value` |

**Verdict:** Baseline RF trained on **120** rows; importance ranking is deterministic at fixed seed.

---

## 2. Top features per lineage group

### Market features

- **Group aggregate importance:** `0.377019`

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `market.magnitude` | 0.127783 |
| 2 | `market.components.price_momentum` | 0.106002 |
| 3 | `market.components.arrival_momentum` | 0.081204 |
| 4 | `market.value` | 0.062031 |
| 5 | `market.confidence` | 0.000000 |
| 6 | `market.direction` | 0.000000 |

### Futures features

- **Group aggregate importance:** `0.366655`

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `futures.components.basis_futures_spot` | 0.143894 |
| 2 | `futures.value` | 0.127866 |
| 3 | `futures.components.curve_slope` | 0.094894 |
| 4 | `futures.confidence` | 0.000000 |
| 5 | `futures.direction` | 0.000000 |
| 6 | `futures.magnitude` | 0.000000 |

### Weather features

- **Group aggregate importance:** `0.256326`

| Rank | Feature | Importance |
|------|---------|------------|
| 1 | `weather.value` | 0.096030 |
| 2 | `weather.components.rainfall_deviation` | 0.087716 |
| 3 | `weather.components.temperature_stress` | 0.072564 |
| 4 | `weather.direction` | 0.000016 |
| 5 | `weather.confidence` | 0.000000 |
| 6 | `weather.magnitude` | 0.000000 |

---

## 3. Machine-readable summary

```json
{
  "commodity_id": "cotton",
  "feature_count": 18,
  "group_totals": {
    "futures": 0.366654669,
    "market": 0.3770194535,
    "weather": 0.2563258774
  },
  "horizon_days": 30,
  "mode": "fixture",
  "model_source": "fitted_baseline_feature_mismatch",
  "row_count": 120,
  "top_per_group": {
    "futures": [
      {
        "feature": "futures.components.basis_futures_spot",
        "importance": 0.1438941409
      },
      {
        "feature": "futures.value",
        "importance": 0.1278662865
      },
      {
        "feature": "futures.components.curve_slope",
        "importance": 0.0948942416
      },
      {
        "feature": "futures.confidence",
        "importance": 0.0
      },
      {
        "feature": "futures.direction",
        "importance": 0.0
      },
      {
        "feature": "futures.magnitude",
        "importance": 0.0
      }
    ],
    "market": [
      {
        "feature": "market.magnitude",
        "importance": 0.1277829493
      },
      {
        "feature": "market.components.price_momentum",
        "importance": 0.1060019173
      },
      {
        "feature": "market.components.arrival_momentum",
        "importance": 0.0812040555
      },
      {
        "feature": "market.value",
        "importance": 0.0620305314
      },
      {
        "feature": "market.confidence",
        "importance": 0.0
      },
      {
        "feature": "market.direction",
        "importance": 0.0
      }
    ],
    "weather": [
      {
        "feature": "weather.value",
        "importance": 0.096029648
      },
      {
        "feature": "weather.components.rainfall_deviation",
        "importance": 0.0877161986
      },
      {
        "feature": "weather.components.temperature_stress",
        "importance": 0.0725635556
      },
      {
        "feature": "weather.direction",
        "importance": 1.64752e-05
      },
      {
        "feature": "weather.confidence",
        "importance": 0.0
      },
      {
        "feature": "weather.magnitude",
        "importance": 0.0
      }
    ]
  },
  "window_end": "2026-01-16",
  "window_start": "2025-09-19"
}
```

---

## 4. Reproducibility and quality gates

| Gate | Status |
|------|--------|
| Fixed fixture path (`--fixture`) | **PASS** |
| Deterministic `random_state` | **PASS** |
| Lineage prefix grouping | **PASS** |
| `pytest tests/unit/test_forecast_feature_importance.py` | see CI |

### Commands

```bash
uv run python scripts/forecast_feature_importance.py --fixture --write-report

uv run pytest tests/unit/test_forecast_feature_importance.py -q
uv run ruff check forecasting/features forecasting/models scripts/forecast_feature_importance.py
uv run mypy forecasting/features forecasting/models
```

---

*End of PI11 Track C feature importance report.*
