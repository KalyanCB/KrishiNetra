# PI6 Repository Audit — Production Data Foundation

**Date:** 2026-06-04  
**Run:** KDO PI6 mandatory first step (read-only audit)  
**Audited commit:** `894a6a88b73b049c8db98e204f1c8479fc955257` (`894a6a8` — *PI5: data ingestion activation spikes + readiness*)  
**Branch:** `main` (tracks `origin/main` @ audit)  
**Rule:** Evidence from git @ `894a6a8`, PI5 reports, and disk inventory — **do not assume PI6 tracks complete**

---

## 1. Executive Summary

PI6 begins from a **PI5-complete baseline**: E-00/E-01/E-02 shipped, Alembic head **`0008_decision_stack`** @ commit, Agmarknet **spike** modules and **8 cotton observation rows** proven (Telangana proof), weather **HTTP spike only** (no observation table in git). **Production-grade commodity data does not exist yet** — no OGD production fetch, no 24–36 mo backfill, no `data_quality_snapshot` ingest rows, no weather rows in DB.

| Dimension | Verdict @ `894a6a8` |
|-----------|-------------------|
| Schema / registry | **READY** — observations, quality snapshot, cotton v1.0.0 @ `0008` |
| Agmarknet production ingest (E-03-S01) | **NOT STARTED** — mapper/parser only; no live OGD pipeline |
| Historical backfill | **NOT STARTED** — 8 proof rows; 2/4 mandis; 2 dates |
| Weather persistence | **SPIKE ONLY** in git — NASA POWER/IMD modules; **no `weather_observation` DDL @ commit** |
| E-04 signal runtime | **OUT OF SCOPE** — inputs insufficient per PI5 Track E |
| PI6 tracks A–H | **OPEN** — see §7 |

**Working tree note (post-audit):** Migration **`0009_weather_observations`** and Track C artifacts exist **on disk but are not in `894a6a8`** — treat Track C as **WIP** until committed (§8).

---

## 2. Migration State @ `0008_decision_stack`

### 2.1 Alembic head @ commit

| Check | Result | Evidence |
|-------|--------|----------|
| Single head | **`0008_decision_stack`** | `tests/unit/test_alembic_revision_chain.py` @ `894a6a8` |
| Linear chain | `0001` → `0008` (8 revisions) | Same test file |
| `0009_weather_observations` in git | **No** | `git ls-tree 894a6a8` — versions through `0008` only |

### 2.2 Revision `0008_decision_stack` (E-01-S07)

| Field | Value |
|-------|-------|
| File | `backend/app/persistence/migrations/versions/0008_decision_stack.py` |
| `down_revision` | `0007_forecast_and_features` |
| Tables | `user_context`, `decision_session`, `recommendation`, `recommendation_version`, `outcome` |
| Partitioning | Quarterly RANGE on `decision_session.created_at` (Q2 2026 child) |

### 2.3 E-03-relevant chain (observations + quality)

| Revision | File | PI6 relevance |
|----------|------|---------------|
| `0002_reference_entities` | `0002_reference_entities.py` | `commodity`, `region`, `market` FK parents |
| `0003_commodity_registry` | `0003_commodity_registry.py` | `commodity_registry` |
| `0004_data_quality_snapshot` | `0004_data_quality_snapshot.py` | `data_quality_snapshot` (schema only — no ingest rows) |
| `0005_observations_partitioned` | `0005_observations_partitioned.py` | `price_observation`, `arrival_observation` |
| `0006`–`0007` | signals + forecast foundation | Out of PI6 ingest scope |
| `0008` | decision stack | Head @ audit; no observation DDL change |

**Partition gap (inherits PI5 G7):** Initial children `*_2026_06` + DEFAULT only — multi-month backfill (Track B) needs forward partition migrations.

---

## 3. Ingestion Code Inventory @ `894a6a8`

### 3.1 Production path (`backend/app/services/ingest/`)

| Path | Role | Production-ready? |
|------|------|-------------------|
| `ingest/__init__.py` | Package marker | — |
| `ingest/agmarknet/constants.py` | `SOURCE_AGMARKNET`, cotton labels, units | **Spike contract** |
| `ingest/agmarknet/parser.py` | OGD envelope + row → `AgmarknetRecord` | **Spike** — no HTTP client |
| `ingest/agmarknet/market_lookup.py` | `(state, district, market)` → `market_id` | **Spike** — seed-backed lookup |
| `ingest/agmarknet/mapper.py` | Records → price/arrival drafts | **Spike** — no dedupe/persist |

**Absent @ audit:** OGD API client, pagination, retries/backoff, `OGD_API_KEY` env wiring, dedupe by business key, load job/CLI, cron/scheduler.

### 3.2 Spike / proof modules

| Path | Role |
|------|------|
| `spike/agmarknet/population.py` | Fixture → map → append-only repos (PI5 Track C proof) |
| `spike/weather/constants.py` | District centroids, source labels |
| `spike/weather/nasa_power.py` | NASA POWER HTTP spike |
| `spike/weather/imd.py` | IMD REST probe (401 without key) |

### 3.3 Scripts

| Script | Role |
|--------|------|
| `scripts/seed_cotton_baseline.py` | Idempotent E-02 cotton apply |
| `scripts/observation_population_proof.py` | CLI JSON proof for 8-row population |
| `scripts/weather_spike_probe.py` | Live NASA POWER / IMD probe |

### 3.4 Tests (ingest-related)

| Path | Scope |
|------|-------|
| `tests/unit/test_agmarknet_ingest.py` | Parser, mapper, lookup (fixture; optional DB) |
| `tests/unit/test_weather_spike.py` | Spike HTTP (mocked) |
| `tests/integration/test_observation_population.py` | DB population gate @ `kn-test-pg:5433` |

**Explicitly not present @ audit:** production ingest integration tests with live OGD, backfill framework, weather persist job, `data_quality_snapshot` writer tests.

---

## 4. Observation Counts (PI5 Track C Proof)

Source: [OBSERVATION_POPULATION_REPORT.md](./OBSERVATION_POPULATION_REPORT.md) — `uv run python scripts/observation_population_proof.py` @ `DATABASE_URL` → `127.0.0.1:5433/krishinetra` after `alembic upgrade head` → `0008` and cotton seed.

| Table | Cotton / `source=agmarknet` | Notes |
|-------|----------------------------|-------|
| `price_observation` | **7** | Khammam min/max/modal @ `2022-03-26`; Warangal modal @ `2026-06-04` |
| `arrival_observation` | **1** | Khammam @ `2022-03-26` (42.5 t → 425 quintals) |
| **Total** | **8** | **7 price + 1 arrival** |

| Dimension | Value |
|-----------|-------|
| Distinct `as_of_date` | **2** (`2022-03-26`, `2026-06-04`) |
| Markets with any row | **2 / 4** seeded Telangana mandis |
| Markets with rows | `mkt_tg_khammam_apmc`, `mkt_tg_warangal` |
| Markets with zero rows | `mkt_tg_karimnagar`, `mkt_tg_kesamudram` |
| OGD fixture envelope | 4 records → 8 persisted; **1 dropped** (Maize @ unmapped mandi) |

**Idempotency:** Append-only — re-run proof adds duplicate UUID rows (no business-key dedupe yet). Production Track A must implement dedupe per E-03-S01.

**Not persisted @ audit:** `weather_observation`, futures, policy events, `data_quality_snapshot` from ingest.

---

## 5. Registry — Cotton v1.0.0

**Fixture:** `backend/app/persistence/seeds/fixtures/cotton.json`  
**Runner:** `backend/app/persistence/seeds/runner.py` + `scripts/seed_cotton_baseline.py`

| Field | Value |
|-------|-------|
| `commodity_id` | `cotton` |
| Registry `version` | **`1.0.0`** |
| `is_active` | `true` |
| `effective_from` | `2026-06-04` |
| `required_agents` | `Market`, `Futures` |
| `optional_agents` | `Weather`, `Policy`, `Demand`, `Global` |
| `price_sources` | Agmarknet, eNAM |
| `arrival_sources` | Agmarknet |
| Telangana mandis seeded | **4** (`mkt_tg_khammam_apmc`, `mkt_tg_warangal`, `mkt_tg_karimnagar`, `mkt_tg_kesamudram`) |
| `source_identifiers.agmarknet` | Per-market OGD triple on `MarketModel` |

**Gap:** `decision_rules.msp_inr_quintal` absent — Policy agent partial (PI5 Track E). Strict MI blocked without licensed Futures (DS-001).

---

## 6. Weather — Spike-Only Status @ Audit Commit

| Layer | @ `894a6a8` | Evidence |
|-------|-------------|----------|
| NASA POWER HTTP | **Proven** (5/5 Telangana districts HTTP 200) | [WEATHER_SPIKE_REPORT.md](./WEATHER_SPIKE_REPORT.md), `spike/weather/nasa_power.py` |
| IMD PRIMARY | **Gated** — HTTP 401 without API key | `spike/weather/imd.py`, WS-01 |
| `weather_observation` table | **Missing in git** | No migration `0009` @ commit; SI-02 open |
| Weather rows in Postgres | **0** | No DDL → no persist path |
| Production ingest / scheduler | **No** | PI5/PI6 stop rule |

**Tiering (unchanged):** IMD PRIMARY after onboarding; NASA POWER SECONDARY/BACKFILL for dev and gap-fill ([WEATHER_DATA_STRATEGY_V1.md](../research/WEATHER_DATA_STRATEGY_V1.md)).

---

## 7. PI6 Track Gaps (A–H)

Critical path (KDO): **Audit → A (ingest) → B (backfill) → E (quality)**; **C (DDL) → D (NASA persist)**; **F/G** after data; **H** last.

| Track | Charter | @ `894a6a8` | Gap / next action |
|-------|---------|-------------|-------------------|
| **A** | E-03-S01 Agmarknet production ingestion | **OPEN** | Extend `services/ingest/agmarknet/`: OGD resource `9ef84268-d588-465a-a308-a864a43d0070`, pagination, retries, dedupe, `OGD_API_KEY`; deliver `E03_S01_COMPLETION_REPORT.md` |
| **B** | Historical cotton backfill (24 mo min, 36 mo pref) | **OPEN** | 8 rows / 2 dates — need backfill framework, partition DDL (G7), `HISTORICAL_BACKFILL_REPORT.md` |
| **C** | Weather observation DDL + ORM + repos | **OPEN @ commit** | SI-02; **WIP on disk** if `0009` present (§8) |
| **D** | NASA POWER ingest → `weather_observation` | **OPEN** | Blocked on Track C head; cotton belt regions; `NASA_POWER_INGESTION_REPORT.md` |
| **E** | `data_quality_snapshot` coverage/freshness | **OPEN** | Schema @ `0004`; no ingest writer (E-03 G8); `DATA_QUALITY_REPORT.md` |
| **F** | Observation coverage analysis | **OPEN** | `OBSERVATION_COVERAGE_ANALYSIS.md` — 2/4 mandis, sparse dates |
| **G** | Signal readiness assessment | **PARTIAL** | PI5 [SIGNAL_INPUT_READINESS.md](../research/SIGNAL_INPUT_READINESS.md); refresh → `SIGNAL_READINESS_ASSESSMENT.md` after B/C/D/E |
| **H** | PI6 program status + executive summary | **OPEN** | `PI6_PROGRAM_STATUS.md`, `PI6_EXECUTIVE_SUMMARY.md` |

**Inherited E-03 gaps (still block production @ audit):** G2 OGD `api-key`, G6 arrivals channel, G7 partitions, G8 quality snapshot wiring, G10 IMD whitelist, DS-001 unsigned (Track G governance).

---

## 8. Working Tree — Track C WIP (`0009` on Disk)

Audit commit **`894a6a8` does not include `0009`**. If the following exist locally, Track C is **in progress (uncommitted)**:

| Artifact | Typical path |
|----------|----------------|
| Migration | `backend/app/persistence/migrations/versions/0009_weather_observations.py` |
| ORM | `backend/app/persistence/models/weather.py` |
| Repository | `backend/app/persistence/repositories/weather.py` |
| Validation | `backend/app/persistence/validation/weather.py` |
| Tests | `tests/unit/test_weather_observations.py` |
| Report | `docs/reviews/WEATHER_PERSISTENCE_REPORT.md` |

**@ time of audit doc creation:** `0009_weather_observations.py` **present on disk** (untracked); `tests/unit/test_alembic_revision_chain.py` modified to expect head `0009` — **git HEAD remains `0008` until merge commit**.

Do not treat weather persistence as **shipped** until `0009` is committed and `alembic upgrade head` passes in CI.

---

## 9. Top 5 PI6 Blockers

| Rank | Blocker | Impact | Primary track |
|------|---------|--------|---------------|
| **1** | **No production Agmarknet pipeline** — no OGD fetch, dedupe, or repeatable load | Cannot grow corpus beyond spike proof | **A** |
| **2** | **No historical backfill** — 8 rows, 2 dates, 2/4 mandis vs 24–36 mo DVA need | Market z-scores, DVA Track B blocked | **B** |
| **3** | **Weather observations not in production DB @ commit** — spike-only HTTP | E-04 Weather agent blocked (SI-02/W-1–W-3) | **C**, **D** |
| **4** | **`data_quality_snapshot` not populated by ingest** | `agmarknet_lag_hours`, MI quality flags missing | **E** |
| **5** | **DS-001 unsigned** — no licensed NCDEX KAPAS EOD | Strict MI + DVA Track B; `required_agents: Futures` | Governance / **G** |

**Secondary (honorable mention):** Partition DDL for multi-month spans (G7); `OGD_API_KEY` not in `.env.example` (G2); E-04→E-07 runtime not started (PI6 stop rule).

---

## 10. Quality Gates @ Audit Baseline

| Gate | @ `894a6a8` |
|------|-------------|
| `pytest` (no `DATABASE_URL`) | PI5 merge: **79 passed**, 43 skipped |
| `pytest` + `DATABASE_URL` @ 5433 | Observation population integration **pass** (PI5) |
| `alembic upgrade head` | **`0008_decision_stack`** |
| `ruff` / `mypy` | PI5 ingest/spike paths **pass** |
| PI6: backfill reproducible | **Not met** |
| PI6: ingestion repeatable (prod) | **Not met** |

---

## 11. References

| Resource | Path |
|----------|------|
| PI5 executive summary | [PI5_EXECUTIVE_SUMMARY.md](./PI5_EXECUTIVE_SUMMARY.md) |
| E-03 Sprint 0 audit | [E03_SPRINT0_AUDIT.md](./E03_SPRINT0_AUDIT.md) |
| Agmarknet spike | [AGMARKNET_SPIKE_REPORT.md](./AGMARKNET_SPIKE_REPORT.md) |
| Observation population | [OBSERVATION_POPULATION_REPORT.md](./OBSERVATION_POPULATION_REPORT.md) |
| Weather spike | [WEATHER_SPIKE_REPORT.md](./WEATHER_SPIKE_REPORT.md) |
| Signal inputs (PI5) | [SIGNAL_INPUT_READINESS.md](../research/SIGNAL_INPUT_READINESS.md) |
| Migration head | `backend/app/persistence/migrations/versions/0008_decision_stack.py` |
| Cotton seed | `backend/app/persistence/seeds/fixtures/cotton.json` |

---

*End of PI6 repository audit — baseline @ `894a6a8`.*
