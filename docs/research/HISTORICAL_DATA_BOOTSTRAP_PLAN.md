# Historical Data Bootstrap Plan — Phase 1 Cotton

**Date:** 2026-06-04  
**Epic:** E-01 (research) / E-03 (ingest implementation)  
**Status:** Planning — no ingest code in E-01 Phase 3  
**Sources:** TDS-006 §3.6–3.7, [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md), [COTTON_DATA_SOURCE_VALIDATION.md](./COTTON_DATA_SOURCE_VALIDATION.md)

---

## 1. Purpose

Define how KrishiNetra bootstraps **historical** market, arrival, futures, and weather series into partitioned `price_observation` / `arrival_observation` (and future agent inputs) before daily refresh cadence stabilizes.

---

## 2. Source Inventory

| Source | Domain | Typical history | Volume (cotton Phase 1) | Cadence | Storage target |
|--------|--------|-----------------|-------------------------|---------|----------------|
| **Agmarknet** | Mandi spot prices, arrivals | 5–15+ years (product-dependent) | ~50–150 markets × 1–3 price types × 365 rows/yr ≈ **150k–450k price rows/yr** | Daily EOD (DA-008) | `price_observation`, `arrival_observation` |
| **eNAM** | Alternate mandi / auction prices | 3–7 years (API/export dependent) | Subset overlap with Agmarknet; **dedupe by market source_id** | Daily | `price_observation` (`source=ename`) |
| **NCDEX KAPAS** (licensed) | Futures curve, OI | Contract inception; bhav post-UDiFF Jul 2024 cleaner | ~250 trading days/yr × 1 near-month focus | Daily EOD batch | Futures agent inputs → future observation table or feature store (E-03+) |
| **USDA / ICAC** | Global cotton balance, export demand | 10–30 years annual/monthly | Low row count; **structured_signal / Global agent** | Monthly–quarterly | `structured_signal` components (S05+), not mandi observations |
| **Weather (IMD / ERA5 class)** | Rainfall, temperature, acreage proxies | 10–40 years gridded | Daily grid → regional rollups for cotton belts | Daily | Weather agent `signal_components` (acreage in Weather signal per TDS-004) |

---

## 3. Bootstrap Strategy by Layer

### 3.1 Mandi prices and arrivals (Agmarknet primary)

| Phase | Action |
|-------|--------|
| **1 — Schema** | E-01-S04 tables at head `0005` (done Phase 3) |
| **2 — Market graph** | E-02 cotton seed: commodity, regions, markets with `source_identifiers` |
| **3 — Backfill window** | **24 months** minimum for DVA/backtest (TDS-011); stretch to **60 months** if Agmarknet export stable |
| **4 — Load pattern** | Batch INSERT append-only; `validation_status=validated` after QA; `as_of_date` = trade date |
| **5 — Partition ops** | Pre-create monthly children for backfill span (migrations per ADR-002) |
| **6 — Quality** | Populate `data_quality_snapshot` per refresh day once ingest runs (E-03+) |

**Storage:** PostgreSQL hot 7 years (TDS-006 §3.6); cold archive PROPOSED post-7y.

### 3.2 eNAM (secondary spot)

Use only where Agmarknet coverage gaps; map to same `market_id` via `source_identifiers`. Lower priority than Agmarknet for cotton Phase 1.

### 3.3 Futures (NCDEX KAPAS)

Blocked on **DS-001 founder decision + NDU/vendor contract**. Bootstrap plan:

1. Licensed EOD bhav CSV/API → normalized curve fields (`curve_level_near`, OI).
2. Align `as_of_date` with exchange session calendar.
3. Set `futures_feed_ok` on quality snapshots when lag > SLA.

### 3.4 USDA / ICAC (global fundamentals)

Annual/monthly series ingested as **Global/Demand agent inputs**, not mandi `price_observation`. Store in `signal_components` or dedicated staging tables at E-03 design time.

### 3.5 Weather

Regional aggregates keyed by `commodity_id` + `as_of_date`; acreage fields live in Weather `signal_components` (founder clarification). Historical ERA5/IMD backfill **36 months** minimum for seasonal features (TDS-007 alignment).

---

## 4. Volume and Cadence Summary

| Stream | Rows/year (order of magnitude) | Bootstrap rows (24 mo) |
|--------|-------------------------------|-------------------------|
| Price observations | 150k–450k | 300k–900k |
| Arrival observations | 50k–150k | 100k–300k |
| Futures EOD | 250 | 500 |
| Global/Policy staging | <500 | <1k |
| Weather regional daily | 1k–5k | 2k–10k |

Monthly partitions keep range scans bounded (DM2-004).

---

## 5. Risks

| ID | Risk | Mitigation |
|----|------|------------|
| H-01 | Agmarknet API/export gaps pre-2020 | Document coverage; shorten backtest window |
| H-02 | Duplicate mandi keys (Agmarknet vs eNAM) | `source` + `source_identifiers` dedupe rules |
| H-03 | Partition child missing during bulk load | DEFAULT partition + ops calendar |
| H-04 | REQ-071 futures not licensed | No production futures bootstrap until DS-001 resolved |

---

## 6. Dependencies

| Dependency | Blocks bootstrap execution |
|------------|---------------------------|
| E-01-S04 schema | **Met** at `0005` |
| E-02 cotton seed markets | Market FK targets |
| E-03 ingest pipelines | Implementation |
| DS-001 | Futures history |

---

*End of historical data bootstrap plan.*
