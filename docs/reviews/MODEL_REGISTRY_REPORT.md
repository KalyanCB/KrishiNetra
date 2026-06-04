# Model Registry Report — PI11 Track E

**Date:** 2026-06-04  
**PI:** PI11 Track E (KDO — `ForecastModelRegistry`)  
**Workspace:** `2fb4e5b`  
**Prerequisites:** `0007_forecast_and_features`; PI10 `0013_forecast_feature_snapshot`; PI11 Track D `0015_forecast_quality_metric`; head `0016_forecast_model_registry`  
**Specification:** TDS-007 §6; TDS-012 model version pinning; TDS-000 KPI storage

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Trained-model metadata persisted? | **Yes** — `forecast_model_registry` table |
| `forecast_version` extended without duplicating 0007? | **Yes** — optional `forecast_model_registry_id` FK @ `0016` |
| Stores model version, training window, MAE/RMSE/MAPE, feature set id/hash? | **Yes** |
| Insert-only / immutable registry rows? | **Yes** — `ForecastModelRegistryRepository.update()` blocked |
| User-facing forecast API? | **No** — registry service only |

**Overall:** **PASS** — PI11 Track E deliverable ready for baseline training handoff (Tracks A–D).

---

## 2. Schema Baseline (0007)

`forecast_version` already carries `model_version`, `feature_set_ref`, and commodity `registry_id`. Track E adds a **dedicated registry** for training provenance and backtest metrics, linkable at publish time via `forecast_model_registry_id`.

---

## 3. PI11 Extension (0016)

**Revision:** `0016_forecast_model_registry`  
**Revises:** `0015_forecast_quality_metric`

| Object | Change | Purpose |
|--------|--------|---------|
| `forecast_model_registry` | CREATE | Pins trained model identity |
| `forecast_version.forecast_model_registry_id` | ADD nullable FK | Links published forecast to registry entry |
| `uq_forecast_model_registry_version_window_hash` | UNIQUE | Dedupes same version + window + feature hash |

### 3.1 `forecast_model_registry` columns

| Column | Type | Purpose |
|--------|------|---------|
| `forecast_model_registry_id` | UUID PK | Registry entry id |
| `commodity_id` | VARCHAR(64) | Cotton (or other) scope |
| `registry_id` | UUID FK | CommodityRegistry version |
| `model_version` | VARCHAR(64) | Pinned library + artifact string |
| `model_family` | VARCHAR(64) nullable | e.g. `naive_persistence`, `linear_regression`, `random_forest` |
| `horizon_days` | INT | 30 / 60 / 90 (default 30) |
| `training_window_start` / `_end` | DATE | Inclusive training span |
| `metrics` | JSONB | `{mae, rmse, mape}` |
| `feature_set_id` | UUID FK nullable | `feature_set` row used for training |
| `feature_set_hash` | VARCHAR(64) | SHA-256 from feature store |
| `created_at` | TIMESTAMPTZ | Audit |

**Note:** Track D `forecast_quality_metric` stores per–`as_of_date` backtest KPI rows; Track E registry stores **model training registration** (version + window + feature pin). Complementary, not duplicate.

---

## 4. Service Contract

| Method | Behavior |
|--------|----------|
| `ForecastModelRegistryService.register` | Validates window, metrics, hash; inserts registry row |
| `ForecastModelRegistryService.get` | Lookup by `forecast_model_registry_id` |
| `ForecastModelRegistryService.resolve` | Lookup by version + training window + `feature_set_hash` |
| `ForecastModelRegistryRepository.insert_entry` | Normalizes metrics JSON; insert-only |
| `*.update()` | **Blocked** — `ImmutableVersionUpdateError` |

Set `forecast_model_registry_id` on `ForecastVersionModel` at **insert** time (immutable after publish).

---

## 5. Deliverables

| Artifact | Path |
|----------|------|
| Migration | `backend/app/persistence/migrations/versions/0016_forecast_model_registry_pi11.py` |
| ORM | `backend/app/persistence/models/forecast.py` (`ForecastModelRegistryModel`) |
| Validation | `backend/app/persistence/validation/forecast_model_registry.py` |
| Repository | `backend/app/persistence/repositories/forecast.py` (`ForecastModelRegistryRepository`) |
| Service | `backend/app/services/forecast/registry/service.py` |
| Types | `backend/app/services/forecast/registry/types.py` |
| Unit / integration tests | `tests/unit/test_forecast_model_registry.py` |

---

## 6. Tests

| Test module | Unit | Integration (`DATABASE_URL`) |
|-------------|------|------------------------------|
| `test_forecast_model_registry.py` | 7 | 1 |

**PI11 Track E tests:** **8** (`test_forecast_model_registry.py`)

---

## 7. Quality Gates

| Check | Result |
|-------|--------|
| `ruff check` (Track E files) | **PASS** |
| `mypy` (Track E files) | **PASS** (4 source files) |
| `pytest tests/unit/test_forecast_model_registry.py -q` | **PASS** — 7 passed, 1 skipped (no `DATABASE_URL`) |
| `pytest tests/unit/test_alembic_revision_chain.py -q` | **PASS** — head `0016_forecast_model_registry` |
| `alembic upgrade head` | Head `0016_forecast_model_registry` |

---

## 8. Reference Return Values (PI11 Track E)

| Item | Value |
|------|-------|
| Migration revision | `0016_forecast_model_registry` |
| Persistence table | `forecast_model_registry` |
| Registry service path | `backend/app/services/forecast/registry/service.py` |
| PI11 Track E test count | **8** |
| Report path | `docs/reviews/MODEL_REGISTRY_REPORT.md` |

---

*End of Model Registry report — PI11 Track E.*
