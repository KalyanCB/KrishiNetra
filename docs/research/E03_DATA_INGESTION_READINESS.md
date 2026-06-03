# E-03 Data Ingestion Readiness (PI1 Track D, docs only)

| Field | Value |
|-------|-------|
| **Date** | 2026-06-03 |
| **Epic** | E-03 — Ingestion & Observations (future) |
| **PI1 rule** | **No E-03 code** |
| **Inputs** | [COTTON_DATA_SOURCE_VALIDATION.md](./COTTON_DATA_SOURCE_VALIDATION.md), [DS001_FUTURES_VENDOR_DECISION.md](./DS001_FUTURES_VENDOR_DECISION.md), TDS-006, E-02-S04 registry strings |

---

## 1. Purpose

Define acquisition, storage, refresh, and validation strategies for Phase 1 cotton sources so E-03 implementation can start after E-02 active registry and E-01 observation tables (S04) exist.

---

## 2. Source readiness matrix

| Source | REQ | Agent(s) | Acquisition | Storage (target) | Refresh | Validation |
|--------|-----|----------|-------------|------------------|---------|------------|
| **Agmarknet** | REQ-070 | Market | **OGD `api.data.gov.in`** bulk/API preferred; portal Excel fallback | `price_observation`, `arrival_observation` (post-S04) | Daily batch after mandi close | `validation_status` pipeline; `agmarknet_lag_hours` in `data_quality_snapshot`; supersede via `supersedes_id` |
| **eNAM** | REQ-070 | Market (secondary) | Dashboard scrape **or** SFAC data request — **no public API** | Same observation tables; tag `source=enam` | Daily snapshot | Lower confidence; cross-check vs Agmarknet; legal review before scraper |
| **IMD** | REQ-070 | Weather | Public REST (`api.imd.gov.in`) with **IP whitelist**; historical via DSP enrollment | Weather observations / `signal_components` prep | Daily (rainfall); sub-daily optional | Range checks; missing district → penalty; acreage from **non-IMD** sources |
| **USDA FAS** | REQ-070 | Demand, Global | FAS Open Data / PSD SOAP / PSD Online export | Global observation or structured_signal prep | Monthly (WASDE cycle) | Schema version on release; attribute mapping to TDS-007 features |
| **ICAC** | REQ-070 | Demand, Global | World Cotton Database export; Open Data Dashboard download | Same as USDA path | Monthly | **Written Secretariat approval** for commercial embed; terms restrict redistribution |
| **NCDEX KAPAS** | REQ-071 | Futures | **Commercial** — see DS-001; not REQ-070 | Licensed futures observations; `futures_feed_ok` flag | EOD minimum (DA-008) | NDU/sublicense audit; OI/volume thresholds; no portal scrape in prod |

**Futures metadata:** Registry `price_sources` / commercial feed separate from Agmarknet strings (Track C §6).

---

## 3. Per-source strategies

### 3.1 Agmarknet

| Dimension | Strategy |
|-----------|----------|
| **Acquisition** | Register `api.data.gov.in` key; ingest commodity=cotton filter; map mandi codes via `market.source_identifiers` / `region.external_refs` (E-02 region seed) |
| **Storage** | Append-only rows; `as_of_date` DATE; prices as `Numeric`; `market_id` FK |
| **Refresh** | Cron after 18:00 IST + lag buffer; idempotent on (`market_id`, `as_of_date`, `source`, `grade`) |
| **Validation** | Stages: `received` → `validated` (range vs prior day %) → `published`; outlier quarantine; DC-001 lag documented in quality snapshot |

**Blockers:** OGD API key provisioning; mandi→`market_id` mapping table (E-02/E-03).

---

### 3.2 eNAM

| Dimension | Strategy |
|-----------|----------|
| **Acquisition** | P2 — manual CSV export or contractual API; avoid production scraper until legal clearance |
| **Storage** | Optional duplicate price series with `source=enam` |
| **Refresh** | Daily when available |
| **Validation** | Reconcile modal price vs Agmarknet same mandi/day; flag divergence > X% |

**Blockers:** No machine-readable API (confidence Medium–Low in Track C).

---

### 3.3 IMD

| Dimension | Strategy |
|-----------|----------|
| **Acquisition** | Apply for API whitelist; district rainfall endpoint; DSP only for backfill |
| **Storage** | Weather agent inputs → later `structured_signal.signal_components` (S05) |
| **Refresh** | Daily |
| **Validation** | Null rainfall vs historical climatology; whitelist outage → `signals_missing` includes Weather |

**Blockers:** IP whitelist ops; DSP license for deep history.

---

### 3.4 USDA

| Dimension | Strategy |
|-----------|----------|
| **Acquisition** | FAS Open Data API key; PSD `getDatabyCommodity` for cotton; cache release calendar |
| **Storage** | Country-level attributes; link to `commodity_id=cotton` global features |
| **Refresh** | Monthly on WASDE release (+ retry) |
| **Validation** | Revision detection (USDA revises prior months); store `observed_at` vs `as_of_date` separately |

**Blockers:** None critical — **High** automation readiness.

---

### 3.5 ICAC

| Dimension | Strategy |
|-----------|----------|
| **Acquisition** | Secretariat contact for API/export license; until then scheduled dashboard export |
| **Storage** | Align units with USDA for cross-check |
| **Refresh** | Monthly |
| **Validation** | Terms compliance review; dual-source sanity vs USDA stocks |

**Blockers:** Commercial redistribution approval (Track C §3.6).

---

### 3.6 Futures (NCDEX / REQ-071)

| Dimension | Strategy |
|-----------|----------|
| **Acquisition** | Primary: NCDEX-authorized EOD vendor API (DS-001); Fallback: direct NDU bhav CSV |
| **Storage** | Not `price_observation`; dedicated futures observation type or tagged source `futures_feed` |
| **Refresh** | EOD after bhav file stable |
| **Validation** | `futures_feed_ok`; thin OI penalty; curve completeness for near month |

**Blockers:** **DS-001 founder approval + contract** — blocks credible MI and basis (REQ-133).

---

## 4. Cross-cutting ingestion architecture

| Concern | Approach |
|---------|----------|
| **Idempotency** | Natural keys per source; upsert only for config, append for observations |
| **Quality** | E-01-S08 `data_quality_snapshot` per (`commodity_id`, `as_of_date`, `registry_id`) |
| **Events** | PRICE_UPDATED / ARRIVAL_UPDATED deferred until bus (TDS-005); log hooks in E-03 |
| **Replay** | `as_of_date` cutoff reads (TDS-006 §5); no future-dated rows visible |
| **Registry-driven config** | E-02-S04 active registry lists source name strings — ingest reads `get_active_registry` |

---

## 5. Dependency graph (E-03 vs program)

```text
E-01-S04 (observation tables)
  ← E-01-S03 (market FK)
E-01-S08 (data_quality_snapshot)  [parallel with S04 after S10]
E-02-S04 (cotton registry seed)   [source mappings]
DS-001 contract                   [futures path]
  → E-03 ingest jobs
```

---

## 6. Risks

| ID | Risk | Severity |
|----|------|----------|
| I3-R1 | No REQ-071 contract | **Critical** for Futures agent |
| I3-R2 | Agmarknet lag/gaps (DC-001) | High |
| I3-R3 | eNAM automation absent | Medium |
| I3-R4 | ICAC licensing | Medium |
| I3-R5 | Observation tables not migrated (S04) | **Critical** for any ingest code |

---

## 7. Test strategy (E-03 phase)

| Test type | Scope |
|-----------|-------|
| Contract tests | OGD/USDA response → domain DTO |
| Integration | Insert observation + quality snapshot row |
| Reconciliation | Agmarknet vs eNAM same day |
| Failure | Missing futures → `futures_feed_ok=false` |
| CI | Postgres + fixture mandi; no live API in PR (vcr/fixtures) |

---

## 8. Readiness verdict

| Source | Ingest-ready (design) | Production-ready |
|--------|----------------------|------------------|
| Agmarknet | **Yes** (with OGD key) | After S04 + mapping |
| eNAM | **Partial** | No |
| IMD | **Partial** | After whitelist |
| USDA | **Yes** | After S04 |
| ICAC | **Partial** | After license |
| NCDEX futures | **Yes** (design) | After DS-001 contract |

**E-03 code gate:** E-01-S04 + S08 + E-02-S04 + DS-001 sign-off.
