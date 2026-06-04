# Agmarknet Production Onboarding — E-03 Operations

**Date:** 2026-06-04  
**PI:** PI4 Track D (KDO — docs only)  
**Status:** Ready for E-03 implementation handoff  
**Product truth:** `docs/founder/` (DC-001 lag/gaps, DD-001 Market domain), TDS-006, TDS-009  
**Synthesized from:** [AGMARKNET_DATA_PROOF.md](./AGMARKNET_DATA_PROOF.md) (PI3 wire format + mapping), [AGMARKNET_REALITY_CHECK.md](./AGMARKNET_REALITY_CHECK.md) (PI2 access + bootstrap)  
**Related:** [AGMARKNET_INGESTION_SPIKE.md](./AGMARKNET_INGESTION_SPIKE.md), [E03_DATA_INGESTION_READINESS.md](./E03_DATA_INGESTION_READINESS.md), [PHASE1_SOURCE_DECISIONS.md](./PHASE1_SOURCE_DECISIONS.md)

---

## 1. Purpose

This document is the **production operations runbook** for Phase 1 Agmarknet ingest (REQ-070, Market agent). It covers account registration, API key handling, rate and pagination constraints, historical backfill, and daily refresh — without ingest implementation.

**Research already complete:** OGD JSON wire format, field ids, cotton string labels, Telangana/Khammam/Warangal portal evidence, and source → `price_observation` / `arrival_observation` mapping are in the PI3 data proof. E-03 owns jobs, secrets storage, and partition load.

---

## 2. Source Authority (Production Path)

| Layer | Authority | Production use |
|-------|-----------|----------------|
| Origin | AGMARKNET (DMI, MoA&FW) | Mandi reporting truth |
| Open distribution | OGD India — “Current daily price… (Mandi)” | [Catalog](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi) |
| Programmatic access | OGD Data API resource `9ef84268-d588-465a-a308-a864a43d0070` | Daily refresh + date-window API backfill |
| Bulk history | OGD catalog zip | Multi-year bootstrap (preferred for volume) |
| License | NDSAP (catalog page) | Attribution + registered `api-key` |
| **Not in scope** | First-party REST on `agmarknet.gov.in` | **Undocumented** — do not assume |
| **Not in scope** | Third-party mirrors (e.g. MKisan) | Avoid for production |

**API base:** `GET https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`

---

## 3. Registration

### 3.1 Who registers

Platform ops or E-03 owner registers **one production OGD account** per environment (prod/staging). Keys must not be committed to the repository.

### 3.2 Steps (evidence-backed)

| Step | Action |
|------|--------|
| 1 | Create account at [data.gov.in](https://data.gov.in) |
| 2 | Log in → **My Account** → generate API key ([OGD Help](https://www.data.gov.in/help)) |
| 3 | Declare use under **National Data Sharing and Accessibility Policy (NDSAP)** on the mandi catalog page |
| 4 | Plan **1–2 sprint lead time** for key provisioning (E-03 Sprint 0 blocker per [E03_DATA_INGESTION_READINESS.md](./E03_DATA_INGESTION_READINESS.md)) |

### 3.3 Access paths after registration

| Path | Auth | E-03 role |
|------|------|-----------|
| **OGD Data API** (preferred) | Registered `api-key` | Daily refresh; batched date-window backfill |
| **OGD bulk zip** | NDSAP open data; purpose on download | 24–60 month (and stretch 10-year) bootstrap |
| **Agmarknet 2.0 UI** | None (manual) | QA, gap spot-check |
| **India Gov Services Excel** | None | Fallback only |

---

## 4. API Keys

### 4.1 Production vs demo

| Key type | Behavior | Use |
|----------|----------|-----|
| **None** | `{"error": "Authorization field missing"}` | Invalid |
| **Invalid / unregistered placeholder** | `Key not authorised` | Expected until prod key issued |
| **Public demo key** (documented on [API resource page](https://data.gov.in/resources/current-daily-price-various-commodities-various-markets-mandi/api)) | Returns metadata + small `records[]` slice | Wire-format tests only; **not** national cotton backfill |
| **Registered production key** | Full filtered queries | **Required** for cotton, Khammam, Warangal production rows |

**Verified 2026-06-04 (demo key):** `filters[state]=Telangana` returned 2 rows (non-cotton); `filters[commodity]=Cotton` returned `total: 0`. Cotton and target mandis require a **registered** key or catalog zip — not absence from AGMARKNET nationally.

### 4.2 Storage and rotation (E-03)

| Requirement | Detail |
|-------------|--------|
| Secret store | Environment variable or vault; never in git |
| Staging | Separate key or scoped test filters |
| CI | Fixture JSON only; no live API in PR (per E-03 test strategy) |
| Rotation | Re-issue via My Account; update deploy secrets; no downtime ingest if dual-key window supported |

### 4.3 Request parameters (reference)

| Parameter | Value | Notes |
|-----------|-------|-------|
| `api-key` | Production secret | Required on every pull |
| `format` | `json` | Primary |
| `limit` | up to `1000` | Per page |
| `offset` | `0`, then increment | Pagination |
| `filters[commodity]` | `Cotton`, `Kapas`, `Cotton (Unginned)` | Repeat pulls; string labels only |
| `filters[state]` | e.g. `Telangana` | Phase 1 belt |
| `filters[district]` | e.g. `Khammam`, `Warangal` | After E-02 market audit |
| `filters[arrival_date]` | `DD/MM/YYYY` windows | Batched backfill |

**Commodity IDs:** There is **no numeric `commodity_id`** in OGD. Normalize portal strings via E-02 registry (`cotton`; exclude `Cotton Seed` from cotton ingest).

---

## 5. Rate Limits and Pagination

| Constraint | Detail | Mitigation |
|------------|--------|------------|
| Demo key corpus | ~10 commodities per request; small daily slice (~82 records observed) | Register production key (AR-01) |
| Production pagination | `limit` + `offset`; filter by commodity and date | Batch by `filters[arrival_date]` windows |
| No documented SLA | Retries with exponential backoff | Track `agmarknet_lag_hours` in `data_quality_snapshot` |
| Large history | Single API call cannot load 10 years national cotton | **OGD zip** → staging → batch INSERT; pre-create monthly partitions |
| Idempotency | Business key (`market_id`, `as_of_date`, `source`, `price_type`, `quality_grade`) | Append-only; supersede via `supersedes_id` |

**Arrivals channel:** OGD JSON resource metadata (2026-06-04) lists prices + `arrival_date` but **not** arrival quantity in the live field list. Bulk zip / portal CSV includes `Arrivals (Tonnes)` — E-03 must ingest volume from the channel that carries it, not assume JSON rows always include volume.

---

## 6. Historical Backfill

Aligned with [HISTORICAL_DATA_BOOTSTRAP_PLAN.md](./HISTORICAL_DATA_BOOTSTRAP_PLAN.md) and TDS-011 (**24 months minimum** PROPOSED).

### 6.1 Bootstrap windows

| Window | National cotton belt (price rows) | Feasibility | Conditions |
|--------|-----------------------------------|-------------|------------|
| **24 mo** | ~300k–900k | **Yes** | OGD key or zip; E-02 `market_id` FK; monthly partitions |
| **36 mo** | ~450k–1.35M | **Yes (conditional)** | Same + gap QA |
| **60 mo** | ~750k–2.25M | **Yes (conditional)** | Pre-2020 gaps (H-01); 10–20 day batch load |
| **10 year** | ~1.5–4M order-of-magnitude | **Yes (conditional)** | Engineering effort; within TDS-006 7-year hot retention policy |

| Window | Telangana-only (~15–25 mandis) | Note |
|--------|-------------------------------|------|
| **24 mo** | ~11k–18k price rows | **Insufficient alone** for DVA — multi-state basket required |

### 6.2 Recommended load pattern

| Phase | Action |
|-------|--------|
| 1 | Download OGD catalog **bulk zip** (declare NDSAP purpose) |
| 2 | Filter commodities ∈ {Cotton, Kapas, variants}; map mandi → `market_id` via E-02 |
| 3 | Staging table → batch INSERT; `validation_status=validated` after QA |
| 4 | Pre-create monthly partition children for backfill span (TDS-006 DM2-004) |
| 5 | API date-window pulls only for **gap fill** after zip baseline |

**Duration (order of magnitude):** 24 mo national — 2–5 days COPY after zip download; 60 mo — 10–20 days including QA.

### 6.3 E-02 pre-backfill verification (no code)

Before seeding Khammam / Warangal markets:

1. OGD query: `state=Telangana`, `commodity` ∈ {Cotton, Kapas}, last 30–90 days (production key).
2. Count distinct `market` where `district` ∈ {Khammam, Warangal, …}.
3. Seed only markets with **≥20 reporting days** in window (Phase 1 proposal).
4. Persist exact `market` spelling in `market.source_identifiers.agmarknet`.

---

## 7. Daily Refresh

| Dimension | Strategy |
|-----------|----------|
| **Schedule** | Cron after **18:00 IST** + lag buffer (DA-008) |
| **Query** | Production key; `filters[commodity]` cotton/kapas; prior business day `filters[arrival_date]` |
| **Geography** | National cotton belt + Telangana audit markets per E-02 active registry |
| **Storage** | Append-only `price_observation`; `arrival_observation` when volume present on channel |
| **Pipeline** | `received` → `validated` (range vs prior day %) → `published` |
| **Quality** | Update `data_quality_snapshot.agmarknet_lag_hours`; DC-001 gaps → confidence penalty, **no forward-fill** |
| **Dedupe** | (`market_id`, `as_of_date`, `source`, `price_type`, `quality_grade`) |

**Optional price rows:** Emit separate observations for `min_price` / `max_price` when ingesting full mandi band; modal remains primary for Market agent.

**eNAM:** Secondary confirmatory only (PHASE1_SOURCE_DECISIONS: DEFERRED for automation); does not replace OGD daily path.

---

## 8. Field and Observation Mapping (E-03 Handoff)

| OGD field | KrishiNetra target |
|-----------|-------------------|
| `state`, `district`, `market` | `region` + `market` via E-02 `source_identifiers` |
| `commodity`, `variety`, `grade` | `commodity_id=cotton` + `quality_grade` |
| `modal_price` (INR/quintal) | `price_observation` (`price_type=modal`) |
| `min_price`, `max_price` | Optional sibling observations |
| `arrival_date` (`DD/MM/YYYY`) | `as_of_date` |
| Arrival tonnes (zip/CSV) | `arrival_observation.volume` (unit policy: quintal at ingest) |
| — | `source` = `agmarknet` |

Full worked examples: [AGMARKNET_DATA_PROOF.md](./AGMARKNET_DATA_PROOF.md) §6–7. ORM alignment: E-01-S04 `PriceObservationModel` / `ArrivalObservationModel`.

---

## 9. E-03 Readiness Checklist

Complete **before** first production ingest job:

| # | Gate | Owner | Status |
|---|------|-------|--------|
| 1 | OGD production `api-key` issued and in secret store | Ops / E-03 | **Open** until registered |
| 2 | E-01-S04 observation tables migrated | E-01 | Prerequisite |
| 3 | E-02-S04 cotton registry + mandi `market_id` mapping | E-02 | Prerequisite |
| 4 | Telangana cotton 90-day `market` audit (≥20 days rule) | E-02 / E-03 | **Open** |
| 5 | Arrivals ingest channel chosen (zip vs JSON gap) | E-03 | Confirm column on download path |
| 6 | Monthly partitions pre-created for backfill span | E-03 / DBA | Per bootstrap window |
| 7 | OGD zip archived for 24 mo (min) bootstrap | E-03 ops | **Open** |
| 8 | `data_quality_snapshot` + `agmarknet_lag_hours` wired | E-01-S08 + E-03 | Parallel after S10 |
| 9 | CI uses fixtures only; no demo key in prod cron | E-03 | Design ready |

**E-03 code gate (program):** E-01-S04 + S08 + E-02-S04. Futures (REQ-071) remains blocked on DS-001 — independent of Agmarknet path.

**Ingest-ready verdict:** Agmarknet is **design-ready** with registered OGD key; **production-ready** after S04 + mapping + key (per [E03_DATA_INGESTION_READINESS.md](./E03_DATA_INGESTION_READINESS.md) §8).

---

## 10. Risks (Operations)

| ID | Risk | Mitigation |
|----|------|------------|
| AR-01 | Demo API key limits | Register production key in E-03 Sprint 0 |
| AR-02 | Telangana mandi reporting gaps | `agmarknet_lag_hours`; TDS-009 confidence penalty |
| AR-03 | Commodity string drift | E-02 mapping table |
| AR-04 | Pre-2020 export gaps | Document coverage; shorten backtest (H-01) |
| AR-05 | Duplicate Agmarknet vs eNAM | `source` + `source_identifiers` dedupe |

---

## 11. References

| Document | Role |
|----------|------|
| [AGMARKNET_DATA_PROOF.md](./AGMARKNET_DATA_PROOF.md) | PI3 wire format, cotton labels, mapping examples |
| [AGMARKNET_REALITY_CHECK.md](./AGMARKNET_REALITY_CHECK.md) | PI2 registration, bootstrap feasibility |
| [AGMARKNET_INGESTION_SPIKE.md](./AGMARKNET_INGESTION_SPIKE.md) | Daily/backfill patterns, rate limits |
| [E03_DATA_INGESTION_READINESS.md](./E03_DATA_INGESTION_READINESS.md) | E-03 source matrix and blockers |
| [COTTON_DATA_SOURCE_VALIDATION.md](./COTTON_DATA_SOURCE_VALIDATION.md) | REQ-070 / Market agent |
| [E02_SEED_PREPARATION_PLAN.md](../implementation/E02_SEED_PREPARATION_PLAN.md) | `cotton` + market FK plan |

---

*End of Agmarknet production onboarding — PI4 Track D.*
