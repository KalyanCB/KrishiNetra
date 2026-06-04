# Leakage Audit Report — PI12 Track D (KDO)

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI12 Track D — leakage investigation (PI11 linear 0-error follow-up) |
| **Workspace** | `c64fe65` |
| **Primary horizon** | **30d** |
| **Panel** | PI10 fixture (`forecasting/datasets/fixtures.py`) |
| **Verdict** | **`LEAKAGE_NO`** |

**Scope:** Explain PI11 `linear_regression` MAE=RMSE=MAPE=0 on fixture rolling OOS; distinguish temporal label leakage from synthetic perfect separability.

---

## 1. Executive summary

| Question | Answer |
|----------|--------|
| Does **temporal label leakage** explain 0-error? | **No** — Track B embargo passes; target is not in the feature matrix; `forecasting/backtest/rolling.py` uses expanding index folds only. |
| Does **target derivability from features** explain 0-error? | **Yes (fixture physics, not leakage)** — On the monotonic +15 INR/day fixture, **y = spot + 450** exactly at 30d; linear regression recovers slope 1 and intercept 450. |
| Is `forecasting/backtest/rolling.py` defective? | **No** — train indices strictly precede test indices; OOS pooling is correct. |
| Should PI11 linear 0-error drive E-06 PROCEED? | **No** — fixture is a noise-free affine panel; RF and naive bands are the honest fixture baselines. |

**Root cause:** **Perfect separability on a deterministic affine fixture** (monotonic spot ladder + fixed 30d forward modal), not label leakage in rolling validation or training matrix construction.

---

## 2. PI11 observation (reproduced)

From [FORECAST_BASELINE_REPORT.md](./FORECAST_BASELINE_REPORT.md) @ fixture, 30d, rolling min train 60 / test 20 / step 20:

| Model | MAE (INR) | RMSE (INR) | MAPE (%) | OOS n |
|-------|-----------|------------|----------|-------|
| naive_persistence | 450.00 | 450.00 | 5.7812 | 60 |
| **linear_regression** | **0.00** | **0.00** | **0.00** | 60 |
| random_forest | 164.30 | 185.68 | 2.0981 | 60 |

Naive predicts spot at T; fixture target at T+30 is spot + **450** INR (30 × 15 INR/day). Naive error is therefore constant **450** — consistent with a non-leaky, mis-specified baseline, not a broken metric pipeline.

---

## 3. Code path analysis

### 3.1 Fixture prices (`forecasting/datasets/fixtures.py`)

```python
level = Decimal("6000") + Decimal("15") * offset  # per calendar day
```

Both primary mandis share the same level each day → basket median modal equals that level.

### 3.2 Supervised row (`forecasting/datasets/builder.py`)

- **Spot (feature anchor):** `spot_price_level` = basket modal at **T**
- **Target:** `target_price_level` = basket modal at **T + horizon**
- **Signal features:** PI9 snapshot numerics at **T** only (constant confidences on fixture)

Target is **not** copied into `row.features` or `ForecastTrainingDataset.X` ([`training.py`](../../forecasting/datasets/training.py) maps `y` from `target_price_level` only).

### 3.3 Training matrix (`forecasting/datasets/training.py`)

| Column | Source | Leakage risk |
|--------|--------|--------------|
| `X[:, spot]` | `spot_price_level` @ T | Legitimate covariate |
| `X[:, signal_*]` | snapshot @ T | Legitimate; fixture constants |
| `y` | modal @ T+30 | Held out in sklearn `fit`; not in `X` |

### 3.4 Baseline rolling eval (`forecasting/backtest/rolling.py` + `pipeline.py`)

- Expanding folds: `train_indices = [0, train_end)`, `test_indices = [train_end, train_end+test_size)`
- Each fold: `fit(X[train], y[train])` → `predict(X[test])` vs `y[test]`
- No shuffling; no future rows in train indices

### 3.5 Track B embargo (`backend/app/services/forecast/validation/rolling.py`)

Per fold: `label_realization_date(train) < test_as_of_date` and `train.as_of_date < test.as_of_date`.

**Fixture PI10 30d rows:** `run_rolling_validation` emits folds; **`assert_no_label_leakage` passes on every fold** (see unit test `test_track_b_label_embargo_passes_on_fixture_folds`).

This module is separate from `forecasting/backtest/rolling.py` (index-based sklearn backtest) but both enforce chronological separation.

---

## 4. Algebraic proof (fixture 30d)

Let modal on day index `k` be `m(k) = 6000 + 15k`.

For horizon `h = 30`:

- `spot(T) = m(k)`
- `target(T) = m(k+30) = m(k) + 15×30 = spot(T) + 450`

Empirical check (workspace `c64fe65`):

```text
delta = y - spot  →  unique values: 1, value 450.0
np.polyfit(spot, y, 1) → slope 1.0, intercept 450.0
```

`LinearRegression` with `[spot, signal_*]` achieves intercept **450** and coefficient **1** on spot; residual **0** (within float tolerance) on all 120 in-sample and 60 pooled OOS points.

Signal columns are **constant** on the fixture; they do not identify the affine law — spot alone is sufficient.

---

## 5. Why this is not label leakage

| Leakage class | Present on fixture? | Evidence |
|---------------|---------------------|----------|
| Target in feature dict / `X` | **No** | `target_price_level` ∉ `feature_names` |
| Train label uses info ≥ test feature date | **No** | Track B tests PASS |
| Random train/test split | **No** | Not implemented ([TIME_SERIES_VALIDATION_REPORT](./TIME_SERIES_VALIDATION_REPORT.md)) |
| Future modal in spot column | **No** | `spot` = modal @ T only |

**Interpretation:** The model learns the **true data-generating law of the synthetic fixture**, not an accidental peek at the label column. On live `@5433` panels (noise, regime shifts, missing futures), the same linear spec should **not** hit zero error — regression test perturbs prices and asserts fold MAE > 1 INR.

---

## 6. Comparison to real-data expectation

| Panel | Linear OOS MAE | Mechanism |
|-------|----------------|-----------|
| PI10 monotonic fixture | ~0 | `y = spot + 450` exact |
| Jittered fixture (±50 INR, seed 42) | > 1 per fold | Affine law broken by noise |
| `@5433` database (when loaded) | TBD | Non-synthetic process |

---

## 7. Quality gates

| Gate | Status |
|------|--------|
| `pytest tests/unit/test_fixture_leakage_audit.py` | **PASS** (PI12) |
| `pytest tests/unit/test_rolling_validation.py` | **PASS** (14) |
| `pytest tests/unit/test_forecast_baseline_models.py` | **PASS** |
| Manual repro (`load_fixture_training_dataset` + `evaluate_all_baselines`) | **PASS** |

### Commands

```bash
uv run pytest tests/unit/test_fixture_leakage_audit.py tests/unit/test_rolling_validation.py -q
uv run python scripts/train_forecast_baselines.py --fixture --write-report
```

---

## 8. Verdict and recommendations

| Item | Value |
|------|-------|
| **Verdict** | **`LEAKAGE_NO`** |
| **Root cause** | Deterministic **+15 INR/day** fixture ⇒ **y = spot + 450** at 30d; linear regression **memorizes** affine law with ~0 rolling OOS error |
| **Report path** | `docs/reviews/LEAKAGE_AUDIT_REPORT.md` |
| **E-06 action** | Retain **ITERATE**; use RF + naive on fixture; retrain/compare on `@5433`; do not promote linear 0-error |

---

*End of PI12 Track D leakage audit.*
