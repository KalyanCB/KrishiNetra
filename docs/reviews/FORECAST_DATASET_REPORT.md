# Forecast Dataset Report — PI10 Track D

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI10 Track D (KDO — forecast dataset builder) |
| **Workspace** | `c1bc6eb` |
| **Mode** | `fixture` |
| **Commodity** | `cotton` |
| **Window** | `2025-09-19` → `2026-02-15` |
| **Primary markets** | 2 |
| **Spot dates (basket modal)** | 150 |
| **DATABASE_URL** | `(not used — fixture mode)` |

**Scope:** Dataset export and validation only — no model training.

---

## 1. Executive summary

| Horizon | Row count | Candidate dates | Coverage | Missing (required) |
|---------|-----------|-----------------|----------|-------------------|
| **30d** | **120** | 120 | 1.0000 | 0 |
| **60d** | **90** | 90 | 1.0000 | 0 |
| **90d** | **60** | 60 | 1.0000 | 0 |

**Verdict:** Datasets built for horizons 30/60/90 with leakage-safe targets (realized basket modal at T+h only when spot exists at T).

---

## 2. Row counts per horizon

- **30-day:** `120` rows
- **60-day:** `90` rows
- **90-day:** `60` rows

---

## 3. Coverage and missing values

### 30-day horizon

- **Candidate dates** (spot in window, target date ≤ end): `120`
- **Coverage ratio** (rows / candidates): `1.000000`
- **Missing counts:**
  - `spot_price_level`: 0
  - `target_log_return`: 0
  - `target_price_level`: 0

### 60-day horizon

- **Candidate dates** (spot in window, target date ≤ end): `90`
- **Coverage ratio** (rows / candidates): `1.000000`
- **Missing counts:**
  - `spot_price_level`: 0
  - `target_log_return`: 0
  - `target_price_level`: 0

### 90-day horizon

- **Candidate dates** (spot in window, target date ≤ end): `60`
- **Coverage ratio** (rows / candidates): `1.000000`
- **Missing counts:**
  - `spot_price_level`: 0
  - `target_log_return`: 0
  - `target_price_level`: 0

---

## 4. Export artifacts

JSONL exports written under `/Users/kalyancb/KrishiNetra/data/forecast_datasets`:

- `forecast_target_30d.jsonl`
- `forecast_target_60d.jsonl`
- `forecast_target_90d.jsonl`

---

## 5. Reproducibility and quality gates

| Gate | Status |
|------|--------|
| Fixed fixture path (`--fixture`) | **PASS** |
| `pytest tests/unit/test_forecast_dataset_builder.py` | see CI |
| `ruff check` / `mypy` on `forecasting.datasets` | **PASS** (local) |
| ML training | **Out of scope** |

### Commands

```bash
# Fixture (no DB)
uv run python scripts/build_forecast_datasets.py --fixture --write-report

# Integration DB @ 5433
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/build_forecast_datasets.py --write-report

uv run pytest tests/unit/test_forecast_dataset_builder.py -q
uv run ruff check forecasting/datasets scripts/build_forecast_datasets.py
uv run mypy forecasting/datasets
```

---

*End of PI10 Track D forecast dataset report.*
