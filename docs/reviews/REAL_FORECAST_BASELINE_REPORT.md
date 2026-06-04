# Real Forecast Baseline Report — PI12 Track C (KDO)

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI12 Track C — retrain baselines on real corpus |
| **Workspace** | `c64fe65` |
| **Mode** | `real` |
| **Commodity** | `cotton` |
| **Horizon** | **30d** (TY-01 price level, primary) |
| **Samples** | 1069 |
| **Features** | 1 |
| **Corpus** | `data/forecast_datasets/real_forecast_target_30d.jsonl` |
| **Rolling folds** | 50 (train min 60, test 20, step 20) |

**Scope:** sklearn baselines on exported @5433 basket-modal JSONL only — no fixture, no LLM.

---

## 1. Executive summary

Held-out metrics pool predictions from **expanding-window rolling folds** (`forecasting.backtest.rolling`, PI11 Track B spec). Target: **realized basket modal at T+30**.

| Model | MAE (INR) | RMSE (INR) | MAPE (%) | OOS n | Model artifact |
|-------|-----------|------------|----------|-------|----------------|
| **naive_persistence** | 0.00 | 0.00 | 0.0000 | 1000 | `/Users/kalyancb/KrishiNetra/data/forecast_models/real_30d/naive_persistence.joblib` |
| **linear_regression** | 0.00 | 0.00 | 0.0000 | 1000 | `/Users/kalyancb/KrishiNetra/data/forecast_models/real_30d/linear_regression.joblib` |
| **random_forest** | 0.00 | 0.00 | 0.0000 | 1000 | `/Users/kalyancb/KrishiNetra/data/forecast_models/real_30d/random_forest.joblib` |

**Lowest RMSE (rolling OOS):** `naive_persistence` (0.00 INR).

### Naive comparison

| Check | Result |
|-------|--------|
| Naive persistence RMSE | 0.00 INR |
| Any model beats naive (RMSE)? | **NO** |
| Any model beats naive (MAE)? | **NO** |

**Data note:** `target_price_level` ≡ `spot_price_level` on every row in this export (max |Δ| = 0 INR). Rolling OOS errors are trivially zero for all baselines; treat model ranking as **inconclusive** until TY-01 targets show non-zero forward modal movement.

---

## 2. Model artifacts

Full-corpus fits under `/Users/kalyancb/KrishiNetra/data/forecast_models/real_30d/`:

- `naive_persistence.joblib` → `/Users/kalyancb/KrishiNetra/data/forecast_models/real_30d/naive_persistence.joblib`
- `linear_regression.joblib` → `/Users/kalyancb/KrishiNetra/data/forecast_models/real_30d/linear_regression.joblib`
- `random_forest.joblib` → `/Users/kalyancb/KrishiNetra/data/forecast_models/real_30d/random_forest.joblib`

Metrics JSON: `/Users/kalyancb/KrishiNetra/data/forecast_models/real_30d/baseline_metrics.json`

---

## 3. Feature contract

- Anchor feature: `spot_price_level` (spot at T)
- Additional numeric features: 0 (PI9 snapshots absent on real export)
- Date range: `2023-06-01` → `2026-05-04`

---

## 4. Reproducibility and quality gates

| Gate | Status |
|------|--------|
| Deterministic seeds (`BASELINE_MODEL_SEED=42`) | **PASS** |
| Real JSONL corpus only (no `--fixture`) | **PASS** |
| `pytest tests/unit/test_forecast_baseline_models.py` | see CI |
| `ruff` / `mypy` on `forecasting` baseline modules | **PASS** (local) |

### Commands

```bash
uv run python scripts/train_forecast_baselines.py --real --write-report

DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/train_forecast_baselines.py --real --write-report --sync-services

uv run pytest tests/unit/test_forecast_baseline_models.py -q
uv run ruff check forecasting/datasets/training.py forecasting/backtest/rolling.py \
  forecasting/models scripts/train_forecast_baselines.py
uv run mypy forecasting/datasets/training.py forecasting/backtest/rolling.py forecasting/models
```

---

*End of PI12 Track C real forecast baseline report.*
