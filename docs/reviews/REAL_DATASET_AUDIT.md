# Real Dataset Audit — PI12 Track A (KDO)

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI12 Track A — real corpus vs PI10/PI11 fixture |
| **Workspace** | `@ main` `c64fe65` |
| **DATABASE_URL** | `postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra` |
| **Builder window (DB default)** | `2023-06-01` → `2026-06-03` |
| **Scope** | Audit only — no model training, no decision/LLM |

**References:** `forecasting/datasets/` (`builder.py`, `basket.py`, `fixtures.py`), `scripts/build_forecast_datasets.py`, [FORECAST_DATASET_REPORT.md](./FORECAST_DATASET_REPORT.md) (fixture), PI8/PI10/PI11 restore claims.

---

## 1. Executive summary

| Source | 30d max samples | 60d max samples | 90d max samples |
|--------|-----------------|-----------------|-----------------|
| **Fixture** (`--fixture`) | **120** | **90** | **60** |
| **@5433** (`ForecastDatasetBuilder`, default window) | **1069** | **1039** | **1009** |

**Corpus @5433:** **61,547** validated Agmarknet observations (60,448 price + 1,099 arrival) vs PI8/PI10 claim **61,544** (+3). **8,170** weather rows (≥5,620 restore target). **0** `futures_observation` rows; **0** `signal_snapshot` rows.

**Verdict:** Fixture panels are **~9–11× smaller** than the live basket-modal series and are **synthetic/monotonic** (PI11 linear 0 MAE artifact). Real supervised rows are capped by **1,100** daily basket-modal dates, not raw observation count.

---

## 2. Fixture vs validated Agmarknet (@5433)

### 2.1 Observation inventory

| Table / slice | Count | Notes |
|---------------|------:|-------|
| `price_observation` (cotton, all statuses) | 60,455 | 7 `received`, 60,448 `validated` |
| `arrival_observation` (cotton, all statuses) | 1,100 | 1 `received`, 1,099 `validated` |
| **Validated Agmarknet total** | **61,547** | PI docs cite **61,544** — within +3 |
| `weather_observation` | **8,170** | Exceeds PI8/PI10 **5,620+** restore |
| `futures_observation` | **0** | NCDEX bhav not loaded @5433 |
| `signal_snapshot` (cotton) | **0** | No PI9 snapshots persisted |

### 2.2 Forecast dataset rows (supervised export)

| Mode | 30d | 60d | 90d | Basket modal dates | Raw price rows in builder path |
|------|----:|----:|----:|-------------------:|-------------------------------:|
| **Fixture** | 120 | 90 | 60 | 150 | 300 (150 days × 2 mandis) |
| **@5433** | 1069 | 1039 | 1009 | 1100 | 20,882 validated modal @ 27 primary mandis |

**Fixture contract** (from `fixtures.py` + `test_forecast_dataset_builder.py`): 150 consecutive calendar days, 2 Telangana mandis, monotonic modal; row counts = `150 − h` per horizon with **100% coverage**.

**Commands reproduced:**

```bash
uv run python scripts/build_forecast_datasets.py --fixture
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/build_forecast_datasets.py
```

---

## 3. How many of 61,544 observations feed forecast datasets?

Observations are **not** 1:1 with supervised rows. The PI10 builder pipeline:

1. **Price-only** — `ArrivalObservationModel` is never read by `ForecastDatasetBuilder`.
2. **Validated + modal + primary mandi** — `filter_validated_primary_prices()` (`basket.py`).
3. **Basket spot** — per-date median of per-market modal medians (`basket_modals_by_date()`).
4. **Horizon target** — basket modal at `as_of_date + h` calendar days (`builder._build_from_modals_and_snapshots()`).

| Stage | Count | % of 61,547 validated Agmarknet |
|-------|------:|----------------------------------|
| Validated Agmarknet (price + arrival) | 61,547 | 100% |
| Validated cotton **price** rows | 60,448 | 98.2% |
| Validated price, `price_type = modal` | 20,882 | 33.9% |
| Validated modal in **27** `load_expected_market_ids()` (window-extended fetch) | 20,882 | 33.9% |
| **Unique basket-modal dates** (all-time @5433) | **1,100** | — |
| **Supervised rows @ default window** | **1069 / 1039 / 1009** | — |

**Price-type split (validated cotton price):** modal **20,882**; min **19,783**; max **19,783**. Min/max rows **do not** enter the basket or forecast builder.

**Date coverage:** Basket modals span **2023-06-01** → **2026-06-04** with **no calendar gaps** >1 day in the modal series (daily continuity). Arrival rows (**1,099**) are orthogonal to TY-01..03 price-level targets unless a future builder adds arrival features.

---

## 4. Max possible 30d / 60d / 90d samples (basket modal logic)

Logic matches PI10 `ForecastDatasetBuilder` / `_build_from_modals_and_snapshots()`:

- **Spot:** basket modal at `T` (`as_of_date`).
- **Target:** basket modal at `T + h` (calendar `timedelta`, not business days).
- **Candidate `T`:** `window_start ≤ T ≤ window_end − h`.
- **Row retained** iff both spot and target modals exist on those dates.

### 4.1 @5433 — default script window

| Horizon | Candidate dates | Rows built | Coverage | Max possible (= rows) |
|---------|----------------:|-----------:|---------:|----------------------:|
| **30d** | 1069 | **1069** | 1.0000 | **1069** |
| **60d** | 1039 | **1039** | 1.0000 | **1039** |
| **90d** | 1009 | **1009** | 1.0000 | **1009** |

With the current **1,100** modal dates and **100%** target availability inside the window, **max samples equal built rows** — no additional rows without extending `window_end`, ingesting earlier history, or adding modal dates.

### 4.2 Fixture — PI10 panel

| Horizon | Max samples |
|---------|------------:|
| **30d** | **120** (= 150 − 30) |
| **60d** | **90** (= 150 − 60) |
| **90d** | **60** (= 150 − 90) |

### 4.3 Theoretical upper bound (corpus-limited)

Given **1,100** modal dates and continuous calendar coverage, the corpus-wide upper bound before window clipping is **1,100 − h** per horizon (same formula as fixture). The default DB window clips to the counts in §4.1.

---

## 5. Leakage and alignment risks

| Risk | Severity | Finding |
|------|----------|---------|
| **Future price in features** | Low (target design) | Targets use modal at **T+h** only; spot at **T** is explicit and correct for TY-01. Unit test `test_targets_use_future_modal_without_leakage` enforces this on fixtures. |
| **`observed_at` temporal cutoff** | **Medium (gap vs design)** | [FORECAST_RESEARCH_DESIGN.md](../research/FORECAST_RESEARCH_DESIGN.md) requires `observed_at <= T` for features and post-horizon targets. **`ForecastDatasetBuilder` does not filter on `observed_at`** — only `as_of_date` + calendar horizon. Agmarknet rows typically align `as_of_date` with trade date; late-arriving revisions could leak if `observed_at > T`. |
| **Calendar vs trading-day alignment** | Low @5433 | Horizons use **calendar days**. Current modal series has **daily** dates (no >1-day gaps), so **T+30** exists whenever **T** is in range. Mandi holidays would drop rows if modal dates were sparse (not observed here). |
| **`spot_price_level` in training matrix** | Low (legitimate) | `training.py` includes spot as feature `spot_price_level`; known at **T**, not the label. |
| **Fixture → linear 0 MAE** | **High (evaluation)** | Monotonic fixture spot ≈ target (+15 INR/day × horizon) → near-perfect linear fit; **not indicative of @5433**. |
| **Empty signal features @5433** | **High (feature gap)** | **0** `signal_snapshot` rows → `flatten_snapshot_features()` returns `{}` for all DB rows. Real builds are **spot + target only** unless snapshots are backfilled. |
| **Futures degeneracy** | Medium | **0** futures observations — Futures agent features absent on live DB (PI11 noted). |
| **Fixture vs DB market scope** | Medium | Fixture uses **2** Telangana mandis; DB uses **27** `load_expected_market_ids()` — basket levels differ; not comparable MAPE without harmonizing scope. |
| **Rolling OOS (PI11 baselines)** | Low (method) | `forecasting/backtest/rolling.py` uses time-ordered expanding folds on **as_of_date** order; separate from dataset construction leakage. |

---

## 6. Comparison to PI11 / FORECAST_DATASET_REPORT

| Metric | PI11 / FORECAST_DATASET_REPORT (fixture) | This audit (@5433) |
|--------|------------------------------------------|---------------------|
| 30d rows | 120 | **1069** |
| 60d rows | 90 | **1039** |
| 90d rows | 60 | **1009** |
| Spot dates | 150 | **1100** |
| Linear baseline MAE | 0.00 (artifact) | Not evaluated (audit scope) |
| DATABASE_URL | not used | **5433** |

---

## 7. Reproducibility

```bash
# Fixture row counts
uv run python scripts/build_forecast_datasets.py --fixture

# Live @5433 (default window 2023-06-01 .. 2026-06-03)
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/build_forecast_datasets.py

uv run pytest tests/unit/test_forecast_dataset_builder.py -q
```

---

## 8. Answers (query checklist)

1. **Rows from fixtures vs validated Agmarknet?** Fixture supervised rows: **120 / 90 / 60**; validated Agmarknet corpus: **61,547** obs; forecast-relevant validated **modal** price rows: **20,882** → **1,100** modal dates → **1069 / 1039 / 1009** @5433.
2. **How many of 61,544 feed forecast?** **20,882** price rows feed basket construction; **1,099** arrival rows do not; **≤1,100** daily spot dates cap features; **1069 / 1039 / 1009** labeled rows @ default window.
3. **Max 30d/60d/90d samples (basket modal)?** Fixture: **120 / 90 / 60**; @5433 default window: **1069 / 1039 / 1009** (100% coverage — max equals built).
4. **Leakage risks?** Target timing is sound on `as_of_date`; **`observed_at` not enforced** in builder; fixture linearity inflates metrics; **no signal snapshots** on live DB; calendar-day horizons OK given daily modals.

---

*End of PI12 Track A real dataset audit.*
