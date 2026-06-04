# Real Dataset Expansion Report — PI12 Track B (KDO)

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI12 Track B — real forecast dataset expansion |
| **Workspace** | `@ c64fe65` |
| **DATABASE_URL** | `postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra` |
| **Builder window** | `2023-06-01` → `2026-06-03` (script default) |
| **Export mode** | Database only — **no `--fixture`** |
| **Target** | **≥1,000** supervised rows @ **30d** minimum horizon |

**References:** [REAL_DATASET_AUDIT.md](./REAL_DATASET_AUDIT.md) (Track A), [LEAKAGE_AUDIT_REPORT.md](./LEAKAGE_AUDIT_REPORT.md) (Track D), `scripts/build_forecast_datasets.py`, `forecasting/datasets/builder.py`.

---

## 1. Executive summary

| Horizon | Row count | Target (30d ≥1000) |
|---------|----------:|---------------------|
| **30d** | **1069** | **MET** |
| **60d** | **1039** | MET (informational) |
| **90d** | **1009** | MET (informational) |

**Verdict:** **PASS** — real basket-modal panels exceed the 1,000-row @ 30d bar with **100%** horizon coverage inside the default window. Exports use the `real_` filename prefix under `data/forecast_datasets/`.

---

## 2. Corpus restore @5433

Restore pipeline (seed → belt backfill → validate → weather → NASA POWER) was **not executed** — integration DB already satisfies PI8/PI10 restore thresholds.

| Check | Count | Restore target | Status |
|-------|------:|----------------|--------|
| Validated cotton `price_observation` | **60,448** | ~60k+ | **OK** |
| Validated cotton `arrival_observation` | **1,099** | ~1k+ | **OK** |
| `weather_observation` | **8,170** | ≥5,620 | **OK** |
| `futures_observation` | **0** | optional | **Absent** |
| `signal_snapshot` (cotton) | **0** | optional | **Absent** |

**If empty (ops playbook):**

```bash
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/agmarknet_backfill.py --fixture
DATABASE_URL=... uv run python scripts/observation_validate.py
DATABASE_URL=... uv run python scripts/nasa_power_ingest.py --months 36
```

---

## 3. Data sources in real build

| Source | Used in builder | Rows @5433 | Notes |
|--------|-----------------|----------:|-------|
| `price_observation` (validated, modal, 27 primary mandis) | **Yes** — basket spot/target | 20,882 modal → **1,100** basket dates | TY-01..03 price-level targets |
| `arrival_observation` (validated) | **No** | 1,099 | Not read by `ForecastDatasetBuilder` |
| `weather_observation` | **No** (direct) | 8,170 | Weather not joined in PI10 builder; available for future feature pass |
| `futures_observation` | **No** | 0 | NCDEX bhav not loaded |
| `signal_snapshot` | **Yes** (join) | 0 | No PI9 snapshots → exports are spot + target only |

Real JSONL rows omit fixture `signal_*` keys and use non-monotonic basket modals (e.g. 30d start **9665** INR flat segment vs fixture **6000 + 15×day** ladder).

---

## 4. Export artifacts

| Horizon | Path | Lines |
|---------|------|------:|
| 30d | `data/forecast_datasets/real_forecast_target_30d.jsonl` | **1069** |
| 60d | `data/forecast_datasets/real_forecast_target_60d.jsonl` | **1039** |
| 90d | `data/forecast_datasets/real_forecast_target_90d.jsonl` | **1009** |

**Script enhancement (Track B):** `--filename-prefix real_` on `scripts/build_forecast_datasets.py` → `export_datasets_jsonl(..., filename_prefix=...)`.

Legacy fixture exports (`forecast_target_*d.jsonl` without prefix) are unchanged unless overwritten manually.

---

## 5. Coverage vs fixture

| Mode | 30d | 60d | 90d | Basket modal dates |
|------|----:|----:|----:|-------------------:|
| Fixture (`--fixture`) | 120 | 90 | 60 | 150 |
| **Real @5433** | **1069** | **1039** | **1009** | **1100** |

All three real horizons show **coverage_ratio = 1.0** (every candidate `T` has modal at `T+h`).

---

## 6. Leakage audit (inherited)

Per [LEAKAGE_AUDIT_REPORT.md](./LEAKAGE_AUDIT_REPORT.md):

| Risk | Real build |
|------|------------|
| Temporal label leakage | **No** — target modal at `T+h` only; spot at `T`; unit test `test_targets_use_future_modal_without_leakage` |
| Fixture monotonic 0 MAE | **N/A** — real panel is not the +15 INR/day affine ladder |
| `observed_at` cutoff | **Gap** — builder filters on `as_of_date` only (Track A noted) |
| Rolling OOS | **No random splits** — `forecasting/backtest/rolling.py` time-ordered folds |

---

## 7. Reproducibility

```bash
# Real export (requires populated @5433)
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/build_forecast_datasets.py --filename-prefix real_

uv run pytest tests/unit/test_forecast_dataset_builder.py \
  tests/unit/test_fixture_leakage_audit.py -q
```

---

## 8. Answers (query checklist)

1. **30d / 60d / 90d row counts?** **1069 / 1039 / 1009**
2. **Report path?** `docs/reviews/REAL_DATASET_EXPANSION_REPORT.md`
3. **Target met (≥1000 @ 30d)?** **Yes** — **1069** rows (**+69** above bar)
4. **Corpus restored?** **Skipped** — already above restore floors; playbook in §2 if empty

---

*End of PI12 Track B real dataset expansion report.*
