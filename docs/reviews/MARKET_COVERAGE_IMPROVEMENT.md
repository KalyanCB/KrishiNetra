# Market Coverage Improvement — PI8 Track E

**Date:** 2026-06-04  
**PI:** PI8 Track E (KDO — fixture-based belt market coverage)  
**Workspace:** `058230e`  
**DB:** `postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra`  
**Baseline:** [MARKET_COVERAGE_REPORT.md](./MARKET_COVERAGE_REPORT.md), [E03_S02_COMPLETION_REPORT.md](./E03_S02_COMPLETION_REPORT.md)

---

## 1. Summary

| Metric | Before (Telangana fixture) | After (cotton belt fixture) | Target |
|--------|---------------------------|----------------------------|--------|
| **Markets reporting** (latest `as_of_date`) | **2** / 27 | **18** / 27 | ≥ 10 / 27 |
| **Coverage ratio** | **0.0741** (2÷27) | **0.6667** (18÷27) | Path to ≥ 0.70 |
| **Distinct `market_id` with price rows** | 2 | **18** | ≥ 10 |
| **Price rows** (36-mo window) | 7,693 | **60,445** | — |
| **`overall_quality_score`** (post-backfill DQS) | 0.3161 | **0.5520** | > 0.70 (live OGD) |

Fixture expansion and belt replay **meet the 10+ reporting-market gate** without `OGD_API_KEY`. Nine seeded mandis remain fixture-empty until live OGD or additional fixture tuples.

---

## 2. Changes

### 2.1 Fixture

| Artifact | Action |
|----------|--------|
| `tests/fixtures/agmarknet/ogd_cotton_belt_sample.json` | **Created** — 17 OGD records across 5 states (TG, MH, GJ, AP, KA) |
| `tests/fixtures/agmarknet/ogd_telangana_sample.json` | **Retained** — minimal 4-record CI envelope |

Belt tuples align with [MARKET_COVERAGE_REPORT.md](./MARKET_COVERAGE_REPORT.md) §3 seed triples (Maharashtra, Gujarat, Andhra Pradesh, Karnataka samples plus expanded Telangana).

### 2.2 Default replay path

| Component | Default fixture |
|-----------|-----------------|
| `scripts/agmarknet_backfill.py` | `ogd_cotton_belt_sample.json` |
| `backend/app/spike/agmarknet/population.py` | `ogd_cotton_belt_sample.json` |

### 2.3 Tests

| Module | Additions |
|--------|-----------|
| `tests/unit/test_agmarknet_backfill.py` | Multi-state filter test; ≥12 `market_id` mapper test; dynamic dry-run row count |
| `tests/unit/test_cotton_market_coverage.py` | Belt fixture resolves ≥12 distinct `market_id` values |

---

## 3. Execution (@ 5433)

```bash
export DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra

uv run python scripts/agmarknet_backfill.py --fixture \
  --start-date 2023-06-01 --end-date 2026-06-03
```

| Ingest | Value |
|--------|-------|
| Days fetched | 5,495 (1,099 × 5 states) |
| OGD rows fetched | 20,881 |
| Prices inserted (incremental) | 52,752 |
| Markets expected | 27 |

---

## 4. Markets reporting (18)

Latest trade date: **2026-06-03**.

| State | `market_id` (reporting) |
|-------|-------------------------|
| Telangana (5) | `mkt_tg_khammam_apmc`, `mkt_tg_warangal`, `mkt_tg_karimnagar`, `mkt_tg_kesamudram`, `mkt_tg_nizamabad` |
| Maharashtra (5) | `mkt_mh_amravati`, `mkt_mh_akola`, `mkt_mh_yavatmal`, `mkt_mh_nagpur`, `mkt_mh_wardha` |
| Gujarat (3) | `mkt_gj_rajkot`, `mkt_gj_bhavnagar`, `mkt_gj_patan` |
| Andhra Pradesh (3) | `mkt_ap_guntur`, `mkt_ap_adoni`, `mkt_ap_nandyal` |
| Karnataka (2) | `mkt_ka_raichur`, `mkt_ka_gulbarga` |

### 4.1 Still empty in fixture (9)

`mkt_tg_adilabad`, `mkt_tg_jagtial`, `mkt_tg_mancherial`, `mkt_tg_nalgonda`, `mkt_tg_peddapalli`, `mkt_mh_jalgaon`, `mkt_mh_parbhani`, `mkt_mh_latur`, `mkt_gj_surendranagar`

---

## 5. Validation

| Check | Result |
|-------|--------|
| `AgmarknetMarketLookup` resolves all belt fixture cotton tuples | **PASS** (unit) |
| ≥ 10 distinct `market_id` with price rows @ 5433 | **PASS** (18) |
| `markets_reporting` on latest `as_of_date` | **PASS** (18/27) |
| `pytest` `test_agmarknet_backfill.py`, `test_cotton_market_coverage.py` | **PASS** |
| `ruff` / `mypy` on changed modules | **PASS** |

---

## 6. Coverage ratio improvement

```
Δ coverage_ratio = 18/27 − 2/27 = 16/27 ≈ +0.5926
```

Relative improvement: **9×** reporting mandis on latest date (2 → 18). DQS `overall_quality_score` rose **0.3161 → 0.5520** (+0.2359) from expanded `coverage_ratio` input; live OGD backfill remains required for ≥0.70 and ~19+ mandis.

---

## 7. Follow-ups

1. Add fixture tuples for the nine empty mandis (or run live OGD with `OGD_API_KEY`).
2. Re-run `--stats --write-report` after live belt pull to refresh [HISTORICAL_BACKFILL_REPORT.md](./HISTORICAL_BACKFILL_REPORT.md).
3. OGD 90-day audit per [AGMARKNET_PRODUCTION_ONBOARDING.md](../research/AGMARKNET_PRODUCTION_ONBOARDING.md) before production tuple renames.

---

*End of PI8 Track E market coverage improvement report.*
