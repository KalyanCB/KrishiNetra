# Historical Bootstrap Feasibility — Cotton / Telangana

**Date:** 2026-06-04  
**PI:** PI2 Track F (KDO rerun — research only)  
**Input:** [HISTORICAL_DATA_BOOTSTRAP_PLAN.md](./HISTORICAL_DATA_BOOTSTRAP_PLAN.md), [AGMARKNET_REALITY_CHECK.md](./AGMARKNET_REALITY_CHECK.md), [IMD_FEASIBILITY_ASSESSMENT.md](./IMD_FEASIBILITY_ASSESSMENT.md)  
**Product truth:** TDS-006, TDS-007, TDS-011 (FD-009, FD-020 DVA), founder DC-001  
**Status:** Feasibility analysis — no ingest code; no architecture changes

---

## 1. Purpose

Derive from **HISTORICAL_DATA_BOOTSTRAP_PLAN.md** the quantitative feasibility of Phase 1 cotton bootstrap: row counts, PostgreSQL partitions, storage, calendar duration, and **minimum dataset for DVA** (decision value added / three-strategy backtest per founder FD-020 and TDS-011).

---

## 2. Minimum Dataset for DVA

| Requirement | Source doc | Minimum | Notes |
|-------------|------------|---------|-------|
| Mandi **modal** price history | Bootstrap plan §3.1; TDS-007 §8.2 | **24 months** daily | Train window PROPOSED; promotion holdout **12 months** separate (TDS-007) |
| Arrival history | Bootstrap plan §3.1 | **24 months** | Sparse acceptable; Market agent arrivals |
| Weather regional daily | Bootstrap plan §3.5; WEATHER_SIGNAL_FRAMEWORK | **36 months** | Seasonal features; IMD PRIMARY + NASA/ERA5 BACKFILL |
| Structured signal replay | TDS-006 §5 | Post E-03 agents | Bootstrap loads observations; signals come from agent runs |
| Futures EOD | Bootstrap plan §3.3; DS-001 | Licensed history | **Production DVA with curve benchmark blocked** until REQ-071 resolved |
| Quality snapshots | Bootstrap plan §3.1 step 6 | From first ingest day | `agmarknet_lag_hours`, `futures_feed_ok` |

### 2.1 DVA-critical path without licensed futures

**Minimum viable backtest inputs (exploratory spot-only):**

1. **24 months** Agmarknet cotton **modal** prices for **≥30 primary markets** spanning multiple states (not Telangana-only).
2. **36 months** weather regional daily aggregates (NASA POWER and/or ERA5 BACKFILL acceptable until IMD history licensed).
3. E-02 `market_id` / `region` FK graph seeded with `source_identifiers`.
4. Monthly partitions pre-created for load span.

**Insufficient alone:** Telangana-only (~15–25 mandis) — lacks regime diversity (MSP/CCI proximity, volatility, Agmarknet-degraded segments per TDS-007 §8.3).

**Insufficient without futures:** Full FD-003 / FD-020 **hold-to-curve** benchmark — requires DS-001 (bootstrap plan REQ-071, risk H-04).

---

## 3. Row Count Estimates (from bootstrap plan §4)

### 3.1 National cotton belt (plan assumptions: 50–150 markets)

| Stream | Rows/year (plan) | 24 mo | 36 mo | 60 mo |
|--------|------------------|-------|-------|-------|
| `price_observation` | 150k–450k | **300k–900k** | **450k–1.35M** | **750k–2.25M** |
| `arrival_observation` | 50k–150k | **100k–300k** | **150k–450k** | **250k–750k** |
| Futures EOD | 250 | 500 | 750 | 1,250 |
| Weather regional daily | 1k–5k | **2k–10k** | **3k–15k** | **5k–25k** |
| Global/Policy staging | <500 | <1k | <2k | <3k |

### 3.2 Telangana-focused subset

| Stream | Assumption | 24 mo | 36 mo | 60 mo |
|--------|------------|-------|-------|-------|
| Price | 15–25 mandis × ~365 modal rows | **11k–18k** | 16k–27k | 27k–45k |
| Arrival | ~40% of price markets reporting | **4k–7k** | 6k–11k | 11k–18k |

Use Telangana subset for **regional MI** and Khammam/Warangal UX; use **national belt** volumes for forecast/DVA stability.

### 3.3 Downstream tables (after E-03 agent runs — not bulk-loaded in bootstrap)

| Table | 24 mo estimate (1 commodity, 6 agents) |
|-------|----------------------------------------|
| `structured_signal` | ~2,190–4,380 (6 × 365) |
| `signal_snapshot` | ~365–730 |
| `forecast_version` | ~365–730 published |

---

## 4. Partition Strategy

Per bootstrap plan §3.1 step 5 and TDS-006 **DM2-004** (monthly partitioning sufficient Phase 1 cotton volume):

| Table | Partition key | Children for 60 mo backfill | Ops note |
|-------|---------------|----------------------------|----------|
| `price_observation` | `as_of_date` (monthly) | **60** + DEFAULT | Pre-create before bulk COPY (H-03) |
| `arrival_observation` | `as_of_date` (monthly) | **60** + DEFAULT | Same span as prices |
| `structured_signal` | `as_of_date` (monthly) | **60** if backfilling signals | Usually forward-generated post-ingest |
| `forecast_version` | `as_of_date` (monthly) | **24** at go-live typical | Backfill historical forecasts optional |

**Replay caution ([DATA_SCALE_FORECAST.md](../reviews/DATA_SCALE_FORECAST.md) SC-02):** Backtests >24 months scan many partitions — acceptable with monthly prune + indexes on (`commodity_id`, `as_of_date`).

**Alembic:** Forward migrations or ops script per ADR-002 — E-01 does not auto-create 2016–2026 children.

---

## 5. Storage Estimates (PostgreSQL hot, TDS-006 §3.6)

7-year hot retention policy; cold archive PROPOSED post-7y.

| Scope | Row count (60 mo national) | Storage order of magnitude |
|-------|---------------------------|----------------------------|
| Price + arrival | ~1.0M–3.0M | **100 MB–1.7 GB** data + **30–50%** indexes |
| Weather staging/features | 5k–25k regional days | **<50 MB** |
| Year 1 steady-state (reviews) | 75k–220k price rows | **<500 MB** total hot ([DATA_SCALE_FORECAST.md](../reviews/DATA_SCALE_FORECAST.md)) |

**Verdict:** Storage is **not a blocker** for 60-month cotton bootstrap at Phase 1 scale (DM2-004).

---

## 6. Backfill Duration Estimates

Mapped from bootstrap plan risks and Agmarknet reality check §6:

| Phase | Activity | 24 mo | 36 mo | 60 mo |
|-------|----------|-------|-------|-------|
| 1 | OGD zip download + cotton/kapas filter | 0.5–2 d | 1–3 d | 2–4 d |
| 2 | Partition pre-create | 0.5 d | 0.5 d | 1 d |
| 3 | COPY/INSERT price + arrival | 2–5 d | 5–10 d | 10–20 d |
| 4 | QA, supersede, gap report | 2–5 d | 3–7 d | 5–10 d |
| 5 | Weather BACKFILL (36 mo NASA/ERA5) | 3–7 d | 4–8 d | 5–10 d |
| 6 | `data_quality_snapshot` backfill | 1–2 d | 1–2 d | 1–2 d |

| Target | Total calendar (engineering + ops) |
|--------|-----------------------------------|
| **DVA minimum (24 mo prices + 36 mo weather)** | **~1–2 weeks** |
| **Stretch 60 mo mandi** | **~3–4 weeks** |

---

## 7. Cotton / Telangana — Bootstrap Checklist

| Item | Feasibility | Dependency |
|------|-------------|------------|
| Telangana mandi prices 24 mo | **Yes** | OGD key + E-02 market seed |
| Khammam + Warangal daily | **Conditional** | Per-mandi reporting (DC-001) |
| National belt 24–60 mo | **Yes (conditional)** | Zip + partitions; pre-2020 gaps (H-01) |
| Telangana-only DVA | **No** — insufficient regimes | Add Gujarat, Maharashtra, Karnataka, etc. |
| Weather 36 mo Telangana rollup | **Yes** | NASA POWER SECONDARY; IMD PRIMARY when whitelisted |
| Futures 24–60 mo | **Blocked** | DS-001 / REQ-071 |

---

## 8. Risks (from bootstrap plan §5 + feasibility)

| ID | Risk | Impact | Mitigation |
|----|------|--------|------------|
| H-01 | Agmarknet gaps pre-2020 | Shorter backtest | Document coverage; accept penalty |
| H-02 | Agmarknet vs eNAM duplicate | Inflated counts | `source` dedupe |
| H-03 | Missing partition child | Load failure | DEFAULT partition + ops calendar |
| H-04 | REQ-071 futures not licensed | No curve DVA | DS-001 parallel |
| BF-04 | E-02 market FK open | Blocks INSERT | E-02 before E-03 bulk load |

---

## 9. Dependencies and Current Status

| Dependency | Blocks execution? | Status (PI2) |
|------------|-------------------|--------------|
| E-01-S04 observation schema `0005` | Was blocker | **Met** |
| E-01-S06 forecast schema `0007` | Replay chain | **Met** |
| E-02 cotton seed markets | **Yes** | **Open** |
| E-03 ingest pipelines | **Yes** | **Open** |
| OGD API key | **Yes** | **Open** (register Sprint 0) |
| DS-001 futures | Production DVA | **Blocked** |

---

## 10. Recommendation

| Decision | Detail |
|----------|--------|
| Proceed with bootstrap plan | **Yes** — volumes and storage fit TDS-006 |
| First load target | **24 mo** national cotton prices + **36 mo** weather BACKFILL |
| Telangana | Include Khammam/Warangal in seed after OGD 90-day market audit |
| Defer | 60 mo and 10-year stretches until gap analysis on pre-2020 data |
| Do not start E-03 code | Per PI2 scope — this doc is feasibility only |

---

*End of historical bootstrap feasibility.*
