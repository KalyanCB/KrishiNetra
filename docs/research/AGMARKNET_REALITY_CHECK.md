# Agmarknet Reality Check — Phase 1 Cotton / Telangana

**Date:** 2026-06-04  
**PI:** PI2 Track B (KDO rerun — research only)  
**Status:** Complete — no ingest code; no architecture changes  
**Product truth:** `docs/founder/` (DA-001, DA-003, DC-001, FD-001, FD-030), TDS-006, TDS-009, TDS-011  
**Technical inputs:** [AGMARKNET_INGESTION_SPIKE.md](./AGMARKNET_INGESTION_SPIKE.md), [COTTON_DATA_SOURCE_VALIDATION.md](./COTTON_DATA_SOURCE_VALIDATION.md), [PHASE1_SOURCE_DECISIONS.md](./PHASE1_SOURCE_DECISIONS.md)

---

## 1. Executive Answer

| Question | Answer | Evidence |
|----------|--------|----------|
| API registration required? | **Yes** for production-scale pulls | OGD demo key caps ~10 commodities/request; registered users get API key from [data.gov.in](https://data.gov.in) My Account ([OGD Help](https://www.data.gov.in/help)) |
| Sample payloads available? | **Yes** — JSON/CSV via OGD API and zip | Catalog updated 2026-05-05; fields include State, District, Market, Commodity, Min/Max/Modal, arrivals, date ([OGD catalog](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi)) |
| Cotton commodity IDs? | **String labels only** — no stable numeric ID in OGD schema | Filter `commodity` ∈ {Cotton, Kapas, variety strings}; normalize in E-02/E-03 |
| Telangana / Khammam / Warangal? | **Conditionally covered** when APMCs report | National OGD dump includes state/district/market; cotton traded at Khammam APMC and Warangal belt mandis (e-NAM/aggregator evidence below) |
| 24 / 36 / 60 month bootstrap? | **24 mo: Yes**; **36 mo: Yes (conditional)**; **60 mo: Yes (conditional)** | Bulk zip + batched API; gaps pre-2020 and per-mandi (H-01, DC-001) |

**Phase 1 role (founder/TDS):** Primary Market domain source (DD-001); basis/futures mitigation for lag/gaps is separate (FD-030, REQ-133) — not an Agmarknet substitute.

---

## 2. API Registration and Access Paths

| Path | URL / endpoint | Auth | E-03 role |
|------|----------------|------|-----------|
| **OGD Data API** (preferred) | `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070` | **Register** at [data.gov.in](https://data.gov.in) → login → API key | Daily refresh + date-window backfill |
| **OGD bulk zip** | [Catalog — daily mandi prices](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi) | NDSAP open data; purpose on download | Multi-year historical bootstrap |
| **Agmarknet 2.0 UI** | [agmarknet.gov.in](https://www.agmarknet.gov.in/home) | None (manual) | QA, gap spot-check; farmer UI advertises 365-day price/arrival |
| **India Gov Services** | Commodity-wise daily report portal | None (Excel export) | Fallback only |
| **First-party REST on agmarknet.gov.in** | — | — | **Not documented** — do not assume |

### 2.1 Registration steps (evidence-backed)

1. Create account on [data.gov.in](https://data.gov.in) (registered users may request API access per [OGD Help](https://www.data.gov.in/help)).
2. Generate API key from **My Account** after login.
3. Declare use under **National Data Sharing and Accessibility Policy (NDSAP)** on catalog page.
4. Plan **1–2 sprint lead time** for key provisioning (E-03 blocker in [E03_DATA_INGESTION_READINESS.md](./E03_DATA_INGESTION_READINESS.md)).

### 2.2 Example API request pattern (cotton)

Public documentation and third-party guides show filter-by-commodity (not commodity_id):

```text
GET https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070
  ?api-key={YOUR_KEY}
  &format=json
  &limit=1000
  &offset=0
  &filters[commodity]=Cotton
  &filters[state]=Telangana
```

Repeat with `filters[commodity]=Kapas` and batched `filters[report_date]` or offset pagination. Demo/sample keys on the dataset page are unsuitable for national cotton backfill (~10 commodities per call).

---

## 3. Sample Payload (OGD API)

| OGD field | KrishiNetra mapping (TDS-006) |
|-----------|-------------------------------|
| `state` | `region` (e.g. Telangana) |
| `district` | `region` child (Khammam, Warangal, …) |
| `market` | `market.name` + `source_identifiers.agmarknet` |
| `commodity` / `variety` | Cotton / Kapas filter → `quality_grade` or mapping table |
| `min_price`, `max_price`, `modal_price` | `price_observation` (`price_type`) |
| `arrivals` (when present) | `arrival_observation.volume` |
| `report_date` | `as_of_date` |
| `unit` | Typically quintal (registry unit) |

**Idempotency (ingest design):** (`market_id`, `as_of_date`, `source`, `price_type`, `quality_grade`) — append-only; supersede via `supersedes_id` (spike §7.3).

---

## 4. Cotton Commodity Identification

| Portal label | Ingest note |
|--------------|-------------|
| **Cotton** | Primary national filter |
| **Kapas** | Shankar / unginned variants |
| **Cotton (Unginned)**, **170-CO2**, state-specific grades | Third-party aggregators mirror OGD strings — E-02 normalization required |

**There is no single OGD `commodity_id`.** Commodity is a free-text dimension in the mandi dataset generated from [AGMARKNET Portal](https://www.agmarknet.gov.in/home) (catalog contributor: DMI, Ministry of Agriculture).

**Dedupe:** Same physical mandi/day may appear under variant strings — mapping table owned by E-02 commodity registry, not Agmarknet API.

---

## 5. Telangana / Khammam / Warangal Coverage

| Dimension | Assessment | Evidence |
|-----------|------------|----------|
| **Telangana state** | Major cotton belt; in national OGD when mandis file | Telangana listed among cotton-trading states in mandi aggregators; 247 APMCs in state per public mandi trackers sourcing Agmarknet |
| **Khammam district** | Cotton actively traded | e-NAM blog: cotton lots at **APMC Khammam** (modal prices Rs 9,000–12,001/q, Mar 2022) ([e-NAM blog](https://enam.gov.in/web/blog)) |
| **Warangal district** | Cotton in regional market set | NAARM e-NAM study: **Warangal** among Telangana mandis with cotton modal price series (2017); academic work uses Agmarknet for **Warangal** cotton arrivals/prices |
| **Kesamudram / other TG mandis** | Adjacent belt | e-NAM: Kesamudram APMC cotton (Telangana) |
| **Coverage model** | **Event-driven** per mandi/day | Founder **DC-001**: lag and gaps cap accuracy — missing mandi/day must not be forward-filled into observations |

### 5.1 E-02 verification procedure (no code)

1. OGD query: `state=Telangana`, `commodity` ∈ {Cotton, Kapas}, last 30–90 days.
2. Count distinct `market` where `district` ∈ {Khammam, Warangal, …}.
3. Seed only markets with ≥N reporting days in window (proposed N=20 for Phase 1).
4. Store mandi codes in `market.source_identifiers` / `region.external_refs`.

**eNAM:** Secondary confirmatory only (PHASE1_SOURCE_DECISIONS: DEFERRED for automation); Khammam cotton on e-NAM does not replace OGD as primary path.

---

## 6. Bootstrap Feasibility (24 / 36 / 60 Months)

Aligned with [HISTORICAL_DATA_BOOTSTRAP_PLAN.md](./HISTORICAL_DATA_BOOTSTRAP_PLAN.md) §3.1 and TDS-011 / TDS-007 train-window (**24 months minimum** PROPOSED).

| Window | Price rows (national cotton belt) | Feasibility | Conditions |
|--------|-----------------------------------|-------------|------------|
| **24 mo** | ~300k–900k | **Yes** | OGD key or zip; E-02 market FK; monthly partitions |
| **36 mo** | ~450k–1.35M | **Yes (conditional)** | Same + QA for reporting gaps |
| **60 mo** | ~750k–2.25M | **Yes (conditional)** | Pre-2020 gaps (H-01); 10–20 day batch load |

| Window | Telangana-only (~15–25 mandis) | Note |
|--------|-------------------------------|------|
| **24 mo** | ~11k–18k price rows | **Insufficient alone** for DVA regime coverage — need multi-state basket (Track F) |

**Load pattern (plan):** Batch INSERT append-only; `validation_status=validated` after QA; pre-create monthly partition children (TDS-006 DM2-004; ADR-002).

**Duration (order of magnitude):** 24 mo national — 2–5 days COPY after zip download; 60 mo — 10–20 days including QA (bootstrap plan §6).

**10-year:** Feasible with engineering (~1.5–4M price rows) within TDS-006 **7-year hot** retention — not a single API call ([AGMARKNET_INGESTION_SPIKE.md](./AGMARKNET_INGESTION_SPIKE.md) §4).

---

## 7. Risks

| ID | Risk | Mitigation (product/TDS) |
|----|------|---------------------------|
| AR-01 | Demo API key limits | Register production key in E-03 Sprint 0 |
| AR-02 | Telangana mandi reporting gaps | `agmarknet_lag_hours`; confidence penalty (TDS-009); eNAM secondary only |
| AR-03 | Commodity string drift | E-02 mapping table |
| AR-04 | Pre-2020 export gaps | Document coverage; shorten backtest (H-01) |
| AR-05 | Duplicate Agmarknet vs eNAM | `source` + `source_identifiers` dedupe (H-02) |

---

## 8. Recommendation

| Verdict | Detail |
|---------|--------|
| **Sufficient for Phase 1 Market agent?** | **Yes (conditional)** — OGD API key + official zip; aligns PHASE1_SOURCE_DECISIONS **APPROVED** |
| **Telangana / Khammam / Warangal?** | **Include in seed** after OGD verification; expect gaps |
| **Bootstrap target** | **24 months minimum** (DVA/backtest); stretch **36–60 months** when ops capacity allows |
| **Not in scope** | Architecture or ingest implementation changes |

---

*End of Agmarknet reality check.*
