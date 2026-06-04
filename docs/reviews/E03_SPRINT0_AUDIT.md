# E-03 Sprint 0 Audit — Repository Prerequisites

| Field | Value |
|-------|-------|
| **Date** | 2026-06-04 |
| **PI** | PI5 Track A (KDO — repository audit only) |
| **HEAD (audited)** | `faf3e668d7a42540d23654b3425606067999657e` (`main`) |
| **Migration head** | `0008_decision_stack` |
| **Scope** | Frozen architecture (`docs/founder/*`, `docs/tds/*`, `docs/adrs/*`, `docs/stories/*`); E-03 prerequisites only — **no ingest implementation**, no signal/forecast/decision runtime |
| **Epic state** | E-00, E-01, E-02 **COMPLETE**; E-03 ingest **not started** |

---

## 1. Executive Summary & Verdict

PI5 Track A confirms that **data foundation and cotton registry prerequisites for E-03 are satisfied in the repository**: Alembic head `0008_decision_stack`, partitioned observation DDL/ORM/repos, active cotton v1.0.0 seed with Telangana mandi `source_identifiers`, and PI4 Agmarknet onboarding research on disk. **No E-03 ingest code** exists under `backend/` (expected at audit time). **First production Agmarknet load** and **Track B (licensed DVA)** remain blocked on ops secrets, mapper implementation, and **DS-001** respectively.

### Verdict table

| Dimension | Verdict | Summary |
|-----------|---------|---------|
| **E-03 schema (FK targets)** | **READY** | `price_observation`, `arrival_observation`, `data_quality_snapshot`, reference entities, `commodity_registry` @ head `0008` |
| **E-03 production load** | **NOT READY** | No ingest pipeline; OGD production key absent; mandi mapper and partition backfill plan open |
| **Track B (licensed DVA)** | **NOT READY** | DS-001 unsigned; REQ-071 futures ingest blocked; TDS-007 G3/G4/G6 cannot pass on spot-only |

### Recommendation (audit-only)

| Action | Verdict |
|--------|---------|
| **Authorize E-03 Sprint 0 implementation** | **Yes** — schema, seed, and PI4 research handoff complete |
| **Claim production Agmarknet ingest** | **No** — until G2–G7 implementation gaps close (§5) |
| **Claim Track B DVA readiness** | **No** — until DS-001 closes and licensed futures path is live |

Aligns with [PI4_EXECUTIVE_SUMMARY.md](./PI4_EXECUTIVE_SUMMARY.md): **START E-03** for ingest engineering; Track B remains on founder **DS-001** + licensed feed, not Sprint 0 schema alone.

---

## 2. Migration & Schema Validation

### 2.1 Alembic chain

| Check | Result | Evidence |
|-------|--------|----------|
| Linear head | **PASS** | `tests/unit/test_alembic_revision_chain.py` — single head `0008_decision_stack` |
| Integration upgrade | **PASS (with `DATABASE_URL`)** | `tests/integration/test_alembic_migrations.py` — `alembic_version` = `0008_decision_stack`; tables include observations and decision stack |

**Revision chain (E-03-relevant):**

| Revision | File | Epic | E-03 relevance |
|----------|------|------|----------------|
| `0002_reference_entities` | `backend/app/persistence/migrations/versions/0002_reference_entities.py` | E-01-S03 | `commodity`, `commodity_profile`, `region`, `market` (FK parents) |
| `0003_commodity_registry` | `backend/app/persistence/migrations/versions/0003_commodity_registry.py` | E-01-S10 | `commodity_registry` |
| `0004_data_quality_snapshot` | `backend/app/persistence/migrations/versions/0004_data_quality_snapshot.py` | E-01-S08 | `data_quality_snapshot` (`agmarknet_lag_hours`, `futures_feed_ok`) |
| `0005_observations_partitioned` | `backend/app/persistence/migrations/versions/0005_observations_partitioned.py` | E-01-S04 | `price_observation`, `arrival_observation` |
| `0006`–`0008` | `0006_signals_partitioned.py` … `0008_decision_stack.py` | E-01-S05–S07 | Out of Sprint 0 ingest scope |

Head file: `backend/app/persistence/migrations/versions/0008_decision_stack.py` (`down_revision`: `0007_forecast_and_features`).

### 2.2 Observation schema (E-01-S04)

| Artifact | Path |
|----------|------|
| DDL | `backend/app/persistence/migrations/versions/0005_observations_partitioned.py` |
| ORM | `backend/app/persistence/models/observation.py` |
| Repositories | `backend/app/persistence/repositories/observation.py` |
| Validation | `backend/app/persistence/validation/observation.py` |
| Unit tests | `tests/unit/test_observations.py` |

**Partitioning:** `PARTITION BY RANGE (as_of_date)`; initial child `price_observation_2026_06` / `arrival_observation_2026_06` (2026-06-01 → 2026-07-01) plus **DEFAULT** partition. Comment in `0005`: ops adds future months via forward migration — **backfill beyond June 2026 requires new partition DDL (gap G7).**

**Enums:** `observation_validation_status` — `received`, `validated`, `published`, `superseded`.

**Foreign keys (ingest must satisfy before insert):**

| Column | Parent | ON DELETE |
|--------|--------|-----------|
| `market_id` | `market.market_id` | RESTRICT |
| `commodity_id` | `commodity.commodity_id` | CASCADE |

**Design note:** Observations do **not** FK to `commodity_registry` — registry is read at ingest/quality time via `RegistryService`, not stored on each row (TDS-006 / E-01-S04).

**Append-only contract:** `PriceObservationRepository.insert_observation` / `ArrivalObservationRepository.insert_observation` only; corrections via `supersedes_id` + new row.

**Suggested idempotency keys (PI4 onboarding):** price — `(market_id, as_of_date, source, price_type, quality_grade)`; arrival — `(market_id, as_of_date, source)` (no `quality_grade` on arrivals).

### 2.3 Data quality snapshot (E-01-S08)

| Artifact | Path |
|----------|------|
| DDL | `backend/app/persistence/migrations/versions/0004_data_quality_snapshot.py` |
| ORM | `backend/app/persistence/models/quality.py` |
| Repository | `backend/app/persistence/repositories/quality.py` |

Ingest must supply active `registry_id` from `RegistryService.get_active_config("cotton")` when writing `data_quality_snapshot` rows (gap G8).

### 2.4 Ingest code presence

| Check | Result |
|-------|--------|
| `backend/**/ingest/**` | **Absent** (expected) |
| Agmarknet fetch/map/load jobs | **Absent** |
| Spike-only weather | `backend/app/spike/weather/` (non-production; not E-03 deliverable) |

---

## 3. Registry & Seed Inventory

### 3.1 Cotton fixture

**Path:** `backend/app/persistence/seeds/fixtures/cotton.json`

| Field | Value |
|-------|-------|
| `commodity_id` | `cotton` |
| Registry `version` | `1.0.0` |
| `is_active` | `true` |
| `effective_from` | `2026-06-04` |
| `price_sources` | `Agmarknet`, `eNAM` |
| `arrival_sources` | `Agmarknet` |
| `required_agents` | `Market`, `Futures` |
| `optional_agents` | `Weather`, `Policy`, `Demand`, `Global` |

### 3.2 Telangana regions (5 rows: 1 state + 4 mandi regions)

| `region_id` | Name | Type | `external_refs.agmarknet_*` |
|-------------|------|------|-----------------------------|
| `reg_tg_state` | Telangana | state | `agmarknet_state`: Telangana |
| `reg_tg_khammam` | Khammam | mandi | `agmarknet_district`: Khammam |
| `reg_tg_warangal` | Warangal | mandi | `agmarknet_district`: Warangal |
| `reg_tg_karimnagar` | Karimnagar | mandi | `agmarknet_district`: Karimnagar |
| `reg_tg_kesamudram` | Kesamudram | mandi | `agmarknet_district`: Khammam |

### 3.3 Telangana markets (4 mandis) — `source_identifiers.agmarknet`

| `market_id` | Display name | Agmarknet tuple (state / district / market) |
|-------------|--------------|-----------------------------------------------|
| `mkt_tg_khammam_apmc` | Khammam APMC | Telangana / Khammam / Khammam |
| `mkt_tg_warangal` | Warangal | Telangana / Warangal / Warangal |
| `mkt_tg_karimnagar` | Karimnagar | Telangana / Karimnagar / Karimnagar |
| `mkt_tg_kesamudram` | Kesamudram | Telangana / Khammam / Kesamudram |

**Mapping mechanism:** No separate `mapping_table` migration. Resolution is **JSONB** on `market.source_identifiers` and `region.external_refs` (`MarketModel` in `backend/app/persistence/models/reference.py`). E-03 must implement runtime lookup: OGD `state` / `district` / `market` strings → `market_id` (gap G3).

### 3.4 Registry service & bootstrap

| Component | Path |
|-----------|------|
| `RegistryService` | `backend/app/services/registry/service.py` |
| Re-export | `backend/app/persistence/services/registry_service.py` |
| Public API | `backend/app/api/v1/registry.py` |
| Repository | `backend/app/persistence/repositories/registry.py` |
| Config validation | `backend/app/persistence/validation/registry.py` |
| Seed runner | `backend/app/persistence/seeds/runner.py` |
| Bootstrap script | `scripts/seed_cotton_baseline.py` |

**Import path for E-03/E-04:**

```python
from backend.app.services.registry import RegistryService, RegistryNotFoundError
```

**Behavior:** `get_active_config` caches active cotton registry for 300s; raises `RegistryNotFoundError` if missing. **Caveat:** hard-coded `commodity_id != "cotton"` guard before DB lookup (`service.py` L48–51) — acceptable for Phase 1 reference implementation.

**Runtime dependency chain:**

```text
uv run alembic upgrade head   # → 0008_decision_stack
uv run python scripts/seed_cotton_baseline.py
  → commodity, profile, regions, markets, commodity_registry v1.0.0 active
  → ingest rows: commodity_id=cotton, market_id ∈ seeded set
```

Insert without seed → FK violation on `market_id` / `commodity_id` (see `tests/unit/test_observations.py`).

---

## 4. PI4 Research Traceability

Research on disk supports E-03 Sprint 0; **implementation remains E-03 engineering**.

| Document | Path | E-03 Sprint 0 role |
|----------|------|-------------------|
| Agmarknet production onboarding | `docs/research/AGMARKNET_PRODUCTION_ONBOARDING.md` | OGD registration, key storage, cron, mapping §8, open checklist §9 |
| Agmarknet data proof | `docs/research/AGMARKNET_DATA_PROOF.md` | Live wire format → observation column mapping |
| Agmarknet ingestion spike (PI3) | `docs/research/AGMARKNET_INGESTION_SPIKE.md` | Prior spike notes; PI5 Track B extends |
| E-03 ingestion readiness | `docs/research/E03_DATA_INGESTION_READINESS.md` | Source matrix, blockers, code gate |
| Cotton intelligence model | `docs/research/COTTON_INTELLIGENCE_MODEL_V1.md` | Intelligence context; **no ingest/schema** |
| Signal engine V1 | `docs/research/SIGNAL_ENGINE_V1.md` | Downstream E-04; `agmarknet_lag_hours` in quality |
| Weather data strategy | `docs/research/WEATHER_DATA_STRATEGY_V1.md` | Track E / IMD whitelist (parallel) |
| DVA proof strategy | `docs/research/DVA_PROOF_STRATEGY.md` | Track A vs B; promotion gates |
| DS-001 founder package | `docs/research/DS001_FOUNDER_DECISION_PACKAGE.md` | Track B gate (unsigned) |
| PI4 executive summary | `docs/reviews/PI4_EXECUTIVE_SUMMARY.md` | **START E-03** recommendation |
| E-02 completion | `docs/reviews/E02_COMPLETION_REPORT.md` | Registry + Telangana seed evidence |

**OGD (Agmarknet):** Resource `9ef84268-d588-465a-a308-a864a43d0070` per onboarding; normalize commodity strings to `commodity_id=cotton` (exclude `Cotton Seed` and non-kapas variants — gap G4).

**Arrivals channel:** OGD JSON may not include arrival volume; bulk zip/portal CSV carries `Arrivals (Tonnes)` — E-03 must select channel before populating `arrival_observation.volume` (gap G6).

---

## 5. E-03 Implementation Prerequisites / Gaps (G1–G11)

### 5.1 Satisfied prerequisites

| Prerequisite | Evidence |
|--------------|----------|
| Partitioned observation DDL + ORM + append-only repos | §2.2 |
| Reference entities + JSONB `source_identifiers` | `0002`, `cotton.json` |
| `commodity_registry` + `data_quality_snapshot` schema | `0003`, `0004` |
| Cotton fixture + idempotent `SeedRunner` | `cotton.json`, `runner.py` |
| `RegistryService.get_active_config` | `service.py` |
| Replay cutoff helper | `backend/app/persistence/replay.py` (`list_price_observations_at_cutoff`) |
| PI4 Agmarknet onboarding + data proof | §4 |

### 5.2 Implementation gaps

| ID | Gap | Owner | Status | Notes |
|----|-----|-------|--------|-------|
| **G1** | No E-03 ingest code (fetch, map, load, cron, staging) | E-03 | **OPEN** | No `*ingest*` package under `backend/`; PI5 Track B/C deliver spikes separately |
| **G2** | OGD production `api-key` not in repo / env template | Ops | **OPEN** | Register at `api.data.gov.in`; not in `.env.example` (only `DATABASE_URL`, `REDIS_URL`, etc.) |
| **G3** | No runtime mandi mapper service | E-03 | **OPEN** | Lookup `market` by `source_identifiers->agmarknet` JSON match; no DB mapping table |
| **G4** | OGD commodity string normalization | E-03 | **OPEN** | Cotton / Kapas / Shankar variants → `commodity_id=cotton` in code |
| **G5** | Telangana 90-day mandi audit (≥20 reporting days) | E-02/E-03 | **OPEN** | Per `AGMARKNET_PRODUCTION_ONBOARDING.md` §6.3, checklist #4 |
| **G6** | Arrivals ingest channel (JSON vs zip/CSV volume) | E-03 | **OPEN** | `arrival_observation.volume` requires channel with tonnes |
| **G7** | Partition DDL for multi-month backfill | E-03/DBA | **OPEN** | Only `*_2026_06` + DEFAULT today; 24/36 mo bootstrap needs forward migrations |
| **G8** | `data_quality_snapshot` ingest wiring | E-03 | **OPEN** | Set `agmarknet_lag_hours`, `futures_feed_ok`; FK `registry_id` from active registry |
| **G9** | Fixture-based CI contract tests (no live API in PR) | E-03 | **OPEN** | Per `E03_DATA_INGESTION_READINESS.md` §7 |
| **G10** | IMD IP whitelist (production weather tier) | Ops/E-03 | **OPEN** | NASA POWER for dev/gap-fill per Track E; parallel PI5 Track D |
| **G11** | No `docs/stories/E-03-*` story files | Program | **OPEN** | Epic mapped in `docs/tds/TDS-014-Epic-Mapping.md` only |

### 5.3 TDS-007 promotion gates (context — not Sprint 0 blockers for schema)

For completeness vs Track B, TDS-007 defines **G1–G7** as pre-production **forecast/DVA** gates (`docs/tds/TDS-007-Forecast-Architecture.md` §9): leakage (G1), replay hash (G2), DVA >3% (G3), positive months >70% (G4), forecast success ≥97% (G5), Futures+Market ≥99% days (G6), no LLM (G7). **All remain unmet** until E-03→E-07 pipeline and DS-001 close — distinct from implementation gaps G1–G11 above.

---

## 6. Track B Readiness (DS-001)

**Track B** = licensed production DVA proof per [DVA_PROOF_STRATEGY.md](../research/DVA_PROOF_STRATEGY.md) and [DVA_BACKTEST_PREPARATION.md](../research/DVA_BACKTEST_PREPARATION.md).

| Requirement | Status @ `faf3e66` |
|-------------|-------------------|
| DS-001 founder signature | **OPEN** — [DS001_FOUNDER_DECISION_PACKAGE.md](../research/DS001_FOUNDER_DECISION_PACKAGE.md) memo complete, **unsigned** |
| REQ-071 licensed NCDEX KAPAS EOD | **BLOCKED** — no vendor contract |
| E-03 historical observations in DB | **BLOCKED** — ingest not started (B-02) |
| TDS-007 G6 (Futures + Market ≥99% days) | **BLOCKED** — futures prod ingest requires DS-001 |
| TDS-007 G3/G4 (DVA >3%, >70% positive months) | **DEFERRED** — hold-to-curve undefined without licensed curve |
| Spot-only exploratory Track A | **Allowed** after E-03 spot load — **not** production promotion |

**Verdict: Track B NOT READY.** Sprint 0 schema readiness does not satisfy licensed DVA. Agmarknet spot ingest (E-03) is **independent** of DS-001 per onboarding, but cotton registry `required_agents: [Market, Futures]` and SIGNAL_ENGINE_V1 strict MI rules still penalize or block production MI without futures.

**Near-term parallel path:** E-03 Sprint 0 Agmarknet + weather tiering **while** founder DS-001 sign-off proceeds; do not treat Track A engineering pass as Track B promotion ([DVA_PROOF_STRATEGY.md](../research/DVA_PROOF_STRATEGY.md) §6.1, §8.1).

---

## 7. References

### Code & tests

| Resource | Path |
|----------|------|
| Migration head | `backend/app/persistence/migrations/versions/0008_decision_stack.py` |
| Observations migration | `backend/app/persistence/migrations/versions/0005_observations_partitioned.py` |
| Cotton seed | `backend/app/persistence/seeds/fixtures/cotton.json` |
| Registry service | `backend/app/services/registry/service.py` |
| Alembic chain test | `tests/unit/test_alembic_revision_chain.py` |
| Migration integration test | `tests/integration/test_alembic_migrations.py` |
| Cotton registry integration | `tests/integration/test_cotton_registry.py` |

### Reviews & program

| Resource | Path |
|----------|------|
| PI4 executive summary | `docs/reviews/PI4_EXECUTIVE_SUMMARY.md` |
| E-02 completion | `docs/reviews/E02_COMPLETION_REPORT.md` |
| PI4 program status | `docs/implementation/PI4_PROGRAM_STATUS.md` |

### Research (PI4 / PI5)

| Resource | Path |
|----------|------|
| E-03 readiness | `docs/research/E03_DATA_INGESTION_READINESS.md` |
| Agmarknet onboarding | `docs/research/AGMARKNET_PRODUCTION_ONBOARDING.md` |
| Agmarknet data proof | `docs/research/AGMARKNET_DATA_PROOF.md` |
| DS-001 package | `docs/research/DS001_FOUNDER_DECISION_PACKAGE.md` |
| DVA proof strategy | `docs/research/DVA_PROOF_STRATEGY.md` |
| DVA backtest prep | `docs/research/DVA_BACKTEST_PREPARATION.md` |
| TDS-007 gates | `docs/tds/TDS-007-Forecast-Architecture.md` |

### Architecture

| Resource | Path |
|----------|------|
| TDS-006 data model | `docs/tds/TDS-006-Data-Model.md` (observations §3.6–3.7) |
| Epic mapping | `docs/tds/TDS-014-Epic-Mapping.md` |

---

*End of E-03 Sprint 0 audit.*
