# E-03-S02 Completion Report — Cotton Belt Historical Backfill

**Date:** 2026-06-04  
**Story:** E-03-S02 — Agmarknet historical backfill (PI7 Track A)  
**HEAD:** `f72a1fb` + PI7 cotton belt seed (27 markets)  
**Prerequisite:** PI7 Track B — [MARKET_COVERAGE_REPORT.md](./MARKET_COVERAGE_REPORT.md)

---

## 1. Summary

| Question | Answer |
|----------|--------|
| Expected markets (belt) | **27** (`load_expected_market_ids`) |
| OGD states per day | **5** (`load_backfill_ogd_states`) |
| Backfill window | **36 mo** — `2023-06-01` → `2026-06-03` (1,099 days) |
| Execution mode @ 5433 | **Fixture** (`OGD_API_KEY` unset) |
| Price rows (window) | **7,693** |
| Arrival rows (window) | **1,099** |
| Total observation rows | **8,792** |
| Markets with data | **2** / 27 |
| Date span (`as_of_date`) | `2023-06-01` … `2026-06-03` |
| `overall_quality_score` (post-run) | **0.3161** (target **> 0.70**) |
| Quality snapshot persisted? | **Yes** (after commit fix in backfill pipeline) |

---

## 2. Code changes (Track A)

| Area | Change |
|------|--------|
| `expected_markets.py` | Belt loader from `cotton.json`; `load_backfill_ogd_states()` for 5-state OGD pulls; legacy `load_telangana_primary_market_ids()` retained |
| `backfill.py` | Per-day × per-state OGD pulls; fixture replay filters by `state`; default expected markets = full belt; quality snapshot commit |
| `agmarknet_backfill.py` | `--scope belt` default (27 markets); stats/ingest aligned with scope |

---

## 3. Fixture vs live counts

| Mode | `OGD_API_KEY` | OGD pulls (36 mo) | Rows inserted (run) | Markets with data | Notes |
|------|---------------|-------------------|----------------------|-------------------|-------|
| **Fixture** | Not required | 1,099 days × 5 states = 5,495 pulls | 7,672 price + 1,096 arrival | 2 (Telangana fixture only) | Replays `tests/fixtures/agmarknet/ogd_telangana_sample.json`; non-TG states return 0 rows |
| **Live** | Required | Same pull count | Ops-dependent | Up to 27 | National belt coverage; rate-limited (`LIVE_BACKFILL_DAY_DELAY_SECONDS = 0.25`) |

**Executed @ 5433 (2026-06-04):**

```bash
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/agmarknet_backfill.py --fixture --scope belt --months 36
```

**Live repro (when key available):**

```bash
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  OGD_API_KEY=... uv run python scripts/agmarknet_backfill.py --scope belt --months 36
```

---

## 4. Quality score progression

| Stage | `markets_expected` | `markets_reporting` | `coverage_ratio` | `completeness_ratio` | `overall_quality_score` |
|-------|-------------------|---------------------|------------------|----------------------|-------------------------|
| Pre-backfill @ 5433 | — | 0 | — | — | *(no Agmarknet rows)* |
| PI6 DQS sample ([DATA_QUALITY_REPORT.md](./DATA_QUALITY_REPORT.md)) | 4 | 1 | 0.25 | 0.033 | **0.0617** |
| Post E-03-S02 fixture @ 5433 | 27 | 2 | 0.074 | 1.0 | **0.3161** |
| Target (live belt backfill) | 27 | ≥19 | ≥0.70 | ≥0.70 | **> 0.70** |

Fixture mode fills **calendar completeness** (1,099 distinct trade dates) but not **market coverage** (2/27 mandis). Live OGD across all five states is required to approach the **> 0.70** gate.

**Latest `source_health` (fixture):**

```json
{
  "agmarknet": "stale",
  "agmarknet_detail": {
    "markets_expected": 27,
    "markets_reporting": 2,
    "coverage_ratio": 0.0741,
    "window_days": 1099,
    "days_with_data": 1099,
    "completeness_ratio": 1.0,
    "latest_as_of_date": "2026-06-03",
    "anomaly_count": 8792
  }
}
```

---

## 5. Per-market coverage (fixture)

| `market_id` | Distinct dates | Min | Max |
|-------------|----------------|-----|-----|
| `mkt_tg_khammam_apmc` | 1,099 | 2023-06-01 | 2026-06-03 |
| `mkt_tg_warangal` | 1,099 | 2023-06-01 | 2026-06-03 |
| *25 belt mandis* | 0 | — | — |

Warangal rows originate from fixture non-cotton rows mapped when state/district/market align with seed lookup.

---

## 6. Verification

| Check | Result |
|-------|--------|
| `uv run pytest tests/unit/ -m 'not integration'` | **Pass** |
| `uv run ruff check .` | **Pass** |
| `uv run mypy backend/app` | **Pass** |
| Signal runtime | **Not run** (per PI7 scope) |
| `alembic_version` @ 5433 | `0010_partition_backfill` |

---

## 7. Deliverables

| Artifact | Path |
|----------|------|
| Expected markets / OGD states | `backend/app/services/ingest/agmarknet/expected_markets.py` |
| Backfill pipeline | `backend/app/services/ingest/agmarknet/backfill.py` |
| CLI | `scripts/agmarknet_backfill.py` |
| Belt coverage report | `docs/reviews/MARKET_COVERAGE_REPORT.md` |
| **This report** | `docs/reviews/E03_S02_COMPLETION_REPORT.md` |

---

## 8. Follow-up

1. Run **live** backfill with `OGD_API_KEY` on @ 5433 to populate Maharashtra, Gujarat, Andhra Pradesh, and Karnataka mandis.
2. Re-audit OGD market spellings per [MARKET_COVERAGE_REPORT.md](./MARKET_COVERAGE_REPORT.md) §3 before production live load.
3. Refresh `DATA_QUALITY_REPORT.md` after live run when `overall_quality_score` ≥ 0.70.
