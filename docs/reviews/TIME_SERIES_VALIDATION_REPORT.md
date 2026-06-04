# Time-Series Validation Report — PI11 Track B

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI11 Track B (KDO — rolling / expanding walk-forward validation) |
| **Workspace** | `2fb4e5b` |
| **Primary horizon** | **30d** (PI10 TY-01 primary) |
| **Window mode** | `expanding` |
| **Dataset rows @ horizon** | 120 |
| **Folds emitted** | **66** |
| **Min train rows (spec)** | 24 |
| **Train window (sliding)** | n/a (expanding) |
| **Step** | rows=1

**Scope:** Validation fold specification and leakage guards only — **no forecast model inference**, no random train/test splits, no decision-engine integration.

---

## 1. Validation specification

| Parameter | Value | Source |
|-----------|-------|--------|
| Primary horizon | **30d** | [FORECAST_RESEARCH_DESIGN.md](../research/FORECAST_RESEARCH_DESIGN.md) §3; PI10 `FORECAST_HORIZONS` |
| Split policy | **Walk-forward** (expanding or sliding) | FORECAST_RESEARCH_DESIGN §5.1 — **no random splits** |
| Label embargo | `label_date < test_as_of` | TY-* leakage rule §2.1 / §5.6 |
| PI10 dataset integration | `ForecastDatasetRow` @ `forecasting.datasets` | Track D builder / fixture |
| `window_mode` | `expanding` | This run |
| `min_train_rows` | 24 | This run |

### Fold window (code contract)

```text
train: as_of_date < test_as_of_date
       AND as_of_date + horizon_days < test_as_of_date
test:  single ForecastDatasetRow @ test_as_of_date
```

---

## 2. Executive summary

| Check | Status |
|-------|--------|
| Chronological folds only | **PASS** |
| Random shuffle / holdout | **N/A — rejected by design** |
| Label leakage audit (per fold) | **PASS** |
| Forecast model in decision layer | **N/A — out of scope** |

| First test `as_of_date` | `2025-11-12` |
| Last test `as_of_date` | `2026-01-16` |
| Train rows per fold (min / max) | 24 / 89 |

**Verdict:** Rolling-window validation spec is operational for PI10 30d datasets with embargo-safe train pools.

---

## 3. Leakage prevention

| Rule | Enforcement |
|------|-------------|
| Train `as_of_date` strictly before test | `assert_no_label_leakage` |
| Train label realization before test features | `as_of + horizon < test_as_of` |
| Duplicate `as_of_date` in corpus | Rejected at fold build |
| Random `train_test_split` | **Not implemented** |

---

## 4. PI10 dataset integration

| Horizon | PI10 fixture rows | Used in this report |
|---------|-------------------|---------------------|
| **30d** | PI10 Track D | 120 rows (**yes**) |
| **60d** | PI10 Track D | — rows (no) |
| **90d** | PI10 Track D | — rows (no) |

Fixture loader: `dataset_rows_from_pi10_fixture()` → `build_fixture_datasets()` (seed **42**, 120/90/60 rows @ 30/60/90d).

---

## 5. Quality gates

| Gate | Status |
|------|--------|
| `pytest tests/unit/test_rolling_validation.py` | **14 passed** |
| `ruff check` on validation module | **PASS** (local) |
| `mypy` on validation module | **PASS** (local) |
| ML / forecast model inference | **Out of scope** |

### Commands

```bash
uv run pytest tests/unit/test_rolling_validation.py -q
uv run ruff check backend/app/services/forecast/validation/
uv run mypy backend/app/services/forecast/validation/
```

---

## 6. Reference return values (PI11 Track B)

| Item | Value |
|------|-------|
| Report path | `docs/reviews/TIME_SERIES_VALIDATION_REPORT.md` |
| Module | `backend/app/services/forecast/validation/rolling.py` |
| Primary horizon | **30d** |
| Default `window_mode` | `expanding` |
| Folds (this report run) | **66** |
| PI11 unit test count | **14** |

*End of time-series validation report — PI11 Track B.*
