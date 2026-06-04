# Forecast Baseline Report — PI11 Track A

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI11 Track A (KDO — baseline forecast models) |
| **Workspace** | `2fb4e5b` |
| **Mode** | `fixture` |
| **Commodity** | `cotton` |
| **Horizon** | **30d** (TY-01 price level) |
| **Samples** | 120 |
| **Features** | 3 |
| **Rolling folds** | 3 (train min 60, test 20, step 20) |

**Scope:** sklearn baselines only — no LLM, decision engine, or recommendation path.

---

## 1. Executive summary

Held-out metrics pool predictions from **expanding-window rolling folds** (`forecasting.backtest.rolling`). Target: **realized basket modal at T+30**.

| Model | MAE (INR) | RMSE (INR) | MAPE (%) | OOS n | Model artifact |
|-------|-----------|------------|----------|-------|----------------|
| **naive_persistence** | 450.00 | 450.00 | 5.7812 | 60 | `data/forecast_models/30d/naive_persistence.joblib` |
| **linear_regression** | 0.00 | 0.00 | 0.0000 | 60 | `data/forecast_models/30d/linear_regression.joblib` |
| **random_forest** | 164.30 | 185.68 | 2.0981 | 60 | `data/forecast_models/30d/random_forest.joblib` |

**Lowest RMSE (rolling OOS):** `linear_regression` (0.00 INR).

---

## 2. Model artifacts

Full-corpus fits written under `data/forecast_models/{horizon}d/`:

- `naive_persistence.joblib` → `data/forecast_models/30d/naive_persistence.joblib`
- `linear_regression.joblib` → `data/forecast_models/30d/linear_regression.joblib`
- `random_forest.joblib` → `data/forecast_models/30d/random_forest.joblib`

Metrics JSON: `/Users/kalyancb/KrishiNetra/data/forecast_models/baseline_metrics.json`

---

## 3. Feature contract

- Anchor feature: `spot_price_level` (spot at T)
- Signal features: 2 numeric PI9 snapshot fields
- Date range: `2025-09-19` → `2026-01-16`

---

## 4. Reproducibility and quality gates

| Gate | Status |
|------|--------|
| Deterministic seeds (`BASELINE_MODEL_SEED=42`) | **PASS** |
| Fixture training path (no DB) | **PASS** |
| `pytest tests/unit/test_forecast_baseline_models.py` | see CI |
| `ruff` / `mypy` on `forecasting` baseline modules | **PASS** (local) |
| LLM / decision / recommendation | **Out of scope** |

### Commands

```bash
# Fixture (no DB)
uv run python scripts/train_forecast_baselines.py --fixture --write-report

uv run pytest tests/unit/test_forecast_baseline_models.py -q
uv run ruff check forecasting/datasets/training.py forecasting/backtest/rolling.py \
  forecasting/models scripts/train_forecast_baselines.py
uv run mypy forecasting/datasets/training.py forecasting/backtest/rolling.py forecasting/models
```

---

*End of PI11 Track A forecast baseline report.*
