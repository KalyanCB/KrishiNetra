# Data Scale Forecast — KrishiNetra Persistence

**Date:** 2026-06-04  
**Scope:** Review only — no schema changes  
**Baseline:** Phase 1 cotton; TDS-006 §3, §9; head `0005_observations_partitioned`

---

## 1. Assumptions

| Parameter | Year 1 | Year 3 | Year 5 |
|-----------|--------|--------|--------|
| Active commodities | 1 (cotton) | 1–2 | 3–5 |
| Mandi markets / commodity | 100 | 150 | 200 |
| Price types / market / day | 2 | 2 | 3 |
| Domain agents / commodity / day | 6 | 6 | 6 |
| Decision sessions / day (Phase 1) | 50–200 | 500 | 2,000 |
| Forecast versions / commodity / day | 1 published | 1 | 1 |

---

## 2. Row Count Estimates

### 2.1 Observations (partitioned monthly on `as_of_date`)

| Table | Daily inserts | Year 1 | Year 3 | Year 5 |
|-------|---------------|--------|--------|--------|
| `price_observation` | ~200–600 | **75k–220k** | **250k–800k** | **400k–1.2M** cumulative hot |
| `arrival_observation` | ~100–200 | **40k–75k** | **120k–250k** | **200k–400k** cumulative hot |

7-year hot retention (TDS-006): steady-state **~3–5M** price rows at maturity (S04 readiness order-of-magnitude).

### 2.2 Signals and snapshots (S05+ — not yet migrated)

| Table | Year 1 | Year 3 | Year 5 |
|-------|--------|--------|--------|
| `structured_signal` | ~220k (6 × 365) | ~650k | ~1.1M per commodity |
| `signal_snapshot` | ~365 | ~1k | ~2k per commodity |

3-year minimum signal retention → partition pruning valuable at S05.

### 2.3 Forecasts (S06+)

| Table | Year 1 | Year 3 | Year 5 |
|-------|--------|--------|--------|
| `forecast_version` | ~365 published | ~1k | ~2k per commodity |
| `feature_vector` | 10–50× forecast rows | grows with feature store | moderate |

All versions indefinite for replay — storage grows linearly with years (low volume vs observations).

### 2.4 Decisions (S07+)

| Table | Year 1 | Year 3 | Year 5 |
|-------|--------|--------|--------|
| `decision_session` | 20k–75k | 180k | 700k+ |
| `recommendation_version` | same order | same | same |
| `user_context` / `outcome` | 1:1 with sessions | same | same |

Quarterly partition on `decision_session.created_at` per TDS-006 §9 when implemented.

### 2.5 Quality and registry

| Table | Scale |
|-------|-------|
| `data_quality_snapshot` | ~365/commodity/year |
| `commodity_registry` | <50 rows total Phase 1 |

---

## 3. Storage Order of Magnitude

| Horizon | PostgreSQL hot (observations + signals) | Notes |
|---------|----------------------------------------|-------|
| Year 1 | **<500 MB** | Phase 1 cotton |
| Year 3 | **2–5 GB** | + second commodity |
| Year 5 | **8–15 GB** hot | Before cold archive; Redis MI remains cache-only |

---

## 4. Partition and Index Review

| Table | Partition | Index health |
|-------|-----------|--------------|
| `price_observation` | Monthly RANGE `as_of_date` + DEFAULT | Parent indexes on `(commodity_id, as_of_date)`, `(market_id, observed_at)`, `(source, as_of_date)` — **adequate** |
| `arrival_observation` | Monthly RANGE | `(commodity_id, as_of_date)`, `(market_id, observed_at)` — **adequate** |
| `forecast_version` (future) | Monthly RANGE planned | UNIQUE per day + model |
| `structured_signal` (future) | Monthly RANGE planned | UNIQUE per agent/day/registry |
| `decision_session` (future) | Quarterly `created_at` | Session audit queries |

**Ops:** Forward migrations for new months; monitor DEFAULT partition row counts (R-S04-01).

---

## 5. Risks at Scale

| ID | Risk | When |
|----|------|------|
| SC-01 | DEFAULT partition bloat | Month rollover missed |
| SC-02 | Replay scans cross many partitions | Backtest >24 months without prune |
| SC-03 | `signal_ids` JSON snapshot size | Negligible Phase 1 |

---

*End of data scale forecast.*
