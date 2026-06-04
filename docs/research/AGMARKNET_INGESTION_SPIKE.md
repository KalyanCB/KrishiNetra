# Agmarknet Ingestion Spike — Phase 1 Cotton

**Date:** 2026-06-04  
**Epic:** E-03 (implementation) / E-01 Phase 4 (research)  
**Status:** Spike complete — no ingest code  
**Sources:** [COTTON_DATA_SOURCE_VALIDATION.md](./COTTON_DATA_SOURCE_VALIDATION.md), [E03_DATA_INGESTION_READINESS.md](./E03_DATA_INGESTION_READINESS.md), OGD India catalog, Agmarknet 2.0 portal

---

## 1. Purpose

Assess whether Agmarknet can supply **10 years of cotton mandi price and arrival observations** for KrishiNetra bootstrap, daily refresh, and Market agent inputs.

---

## 2. Access Paths

| Path | URL / endpoint | Auth | Best for |
|------|----------------|------|----------|
| **OGD Data API** (preferred) | `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070` | Register at [data.gov.in](https://data.gov.in) for API key; demo key limited (~10 commodities/query) | Programmatic daily + bulk backfill |
| **OGD bulk zip** | [Catalog — Current daily mandi prices](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi) | NDSAP open data; purpose declaration on download | Historical backfill batches |
| **Agmarknet 2.0 UI** | [agmarknet.gov.in](https://agmarknet.gov.in) commodity/market daily reports | None (manual) | QA spot-checks, gap fill |
| **India Gov Services** | [Commodity-wise daily report](https://services.india.gov.in/service/detail/check-agriculture-commodity-and-market-wise-daily-reports-1) | None | Excel export fallback |
| **Third-party mirrors** (e.g. MKisan) | Various REST wrappers | Separate API keys | **Not recommended** for production — prefer official OGD channel |

**No first-party REST API** is documented on `agmarknet.gov.in` itself; E-03 should standardize on **OGD Catalog API + zip archives**.

---

## 3. Payload Shape (OGD API)

Typical fields per record (JSON/CSV):

| Field | Maps to KrishiNetra |
|-------|---------------------|
| State, District, Market | `region.external_refs`, `market.source_identifiers` |
| Commodity, Variety | Filter cotton (`Kapas`, `Cotton`, grade variants) |
| Min / Max / Modal price | `price_observation` (`price_type`, `value`) |
| Arrival quantity | `arrival_observation.volume` |
| Report date | `as_of_date` (DATE) |
| Unit | `unit` (quintal typical) |

Pagination: OGD API supports `limit` / `offset` query params. Bulk zip avoids pagination for large historical pulls.

---

## 4. Historical Depth

| Claim | Assessment |
|-------|------------|
| Portal UI | Date selectors support multi-year commodity reports; farmer-facing views advertise ~365 days |
| OGD catalog | Updated regularly (catalog metadata shows ongoing refresh); zip archives contain **multi-year** national mandi history when downloaded in bulk |
| DACNET statistical reports | Longer analytical series; lower granularity than daily mandi rows |
| **10-year cotton backfill** | **Conditionally yes** — data exists in government archives, but **not via a single paginated API call**. Requires: (1) OGD bulk zip ingestion or repeated API queries by date window, (2) mandi/commodity filter for cotton/kapas, (3) partition pre-creation for 2016–2026 span |

**Answer:** Can we load 10 years cotton observations? **Yes, with engineering effort** — use OGD bulk + batched API backfill; expect **gaps** in mandi reporting (DC-001) and require QA/supersede handling.

---

## 5. Cotton / Mandi Coverage

| Dimension | Notes |
|-----------|-------|
| Commodity names | "Cotton", "Kapas", state-specific variety strings — normalize in E-02/E-03 mapping |
| Markets | Major cotton belts: Gujarat, Maharashtra, Telangana, Karnataka, Punjab, Haryana, Rajasthan, MP — ~50–150 active mandis reporting on typical days |
| Price types | Min, max, modal → store modal as primary; optional min/max rows |
| Arrivals | Reported where mandi submits; sparser than prices |

Phase 1 target: **24–60 months** bootstrap (TDS-011 DVA); 10-year stretch is **ops/storage feasible** (~1.5–4M price rows order-of-magnitude) within TDS-006 7-year hot retention policy.

---

## 6. Rate Limits and Pagination

| Constraint | Mitigation |
|------------|------------|
| Demo API key caps records per request | Register production key; batch by `date` + `commodity` |
| No documented SLA | Retry with backoff; track `agmarknet_lag_hours` in quality snapshot |
| Large backfill | Offline zip → staging → COPY/INSERT; pre-create monthly partitions |
| Idempotency | Unique on (`market_id`, `as_of_date`, `source`, `price_type`, `quality_grade`) at ingest layer |

---

## 7. Ingestion Strategies

### 7.1 Daily refresh

1. Cron after 18:00 IST + lag buffer (DA-008).
2. OGD API query: commodity=cotton/kapas, date=yesterday.
3. Map mandi codes → `market_id`; append-only INSERT.
4. Pipeline: `received` → `validated` → `published`.
5. Update `data_quality_snapshot.agmarknet_lag_hours`.

### 7.2 Historical backfill

1. Download OGD zip for mandi prices (multi-year).
2. Filter cotton commodities; dedupe against existing rows.
3. Batch INSERT with `validation_status=validated` post-QA.
4. Alembic forward migrations add monthly partition children for backfill span.

### 7.3 Gap handling

- Missing mandi/day → confidence penalty (TDS-009); do not forward-fill prices into observations.
- Supersede chain via `supersedes_id` when corrected values arrive.

---

## 8. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Reporting lag / missing mandis (DC-001) | High | Quality snapshot penalties; optional eNAM secondary |
| Commodity string inconsistency | Medium | E-02 mapping table |
| OGD API key provisioning delay | Medium | Start registration in Sprint 0 of E-03 |
| 10-year volume + partition ops | Medium | Pre-create partitions; batch load off-peak |

---

## 9. Recommendation

| Question | Answer |
|----------|--------|
| Sufficient for Phase 1 Market agent? | **Yes** — primary mandi source |
| 10-year cotton load feasible? | **Yes (conditional)** — bulk OGD + batched API; not turnkey |
| Production path | OGD API key + official zip backfill; avoid unofficial aggregators |

---

*End of Agmarknet ingestion spike.*
