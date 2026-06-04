# PI9 Repository Audit — Signal Generation Foundation

**Date:** 2026-06-04  
**Run:** KDO PI9 mandatory first step (read-only audit)  
**Audited commit:** `e9fa355e4a38db28fbcbea2438e91d847c203ac3` (`e9fa355` — *PI8: data validation and publication*)  
**Branch:** `main` @ audit (`HEAD` = `e9fa355`)  
**Rule:** Evidence from git @ `e9fa355`, live query @ `127.0.0.1:5433/krishinetra`, and PI8 reports — **do not assume PI9 tracks complete**

---

## 1. Executive Summary

PI9 begins from a **PI8-complete baseline** in git: E-00/E-01/E-02/E-03 substantially shipped, Alembic head **`0011_observation_validation_rejected`**, Agmarknet validation pipeline operational, signal **schema** @ `0006`, enhanced-degraded signal readiness **approved** (inputs only). **No signal generators, no SignalSnapshot assembly service, no replay proof** exist @ audit commit.

| Dimension | @ `e9fa355` (repo) | @ `127.0.0.1:5433` (live query) | PI8 documented baseline |
|-----------|-------------------|--------------------------------|-------------------------|
| Alembic head | **`0011_observation_rejected`** | Same | Matches |
| Agmarknet obs | Schema + validation **shipped** | **0** price, **0** arrival | **61,544 validated** |
| Weather obs | Schema + NASA ingest **shipped** | **0** weather | **5,620** (`received`) |
| Markets / registry | Code + seeds on disk | **0** markets, **0** `commodity_registry` | **18 / 27** reporting |
| Signal runtime | **Not built** | **0** `structured_signal`, **0** `signal_snapshot` | Enhanced degraded **approved** (inputs only) |
| E-04 stories | **No** `docs/stories/E-04-*.md` | — | TDS-014 + PI9 charter only |

**Critical finding:** Integration Postgres @ **5433 is reachable and at migration `0011`, but the PI8 observation corpus is not loaded** (empty tables, minimal seed). Tracks **A, B, D** cannot be integration-tested on this DB until cotton seed, belt fixture backfill, and validation are re-run. PI8 metrics remain valid as **committed docs + prior run evidence**, not as current @5433 state.

**Working tree note (post-`e9fa355`, not in commit):** Track **F** artifacts — `docs/reviews/E03_PARALLEL_STATUS.md`, `weather_observation_validation_service.py`, `.env.example` / `observation_validate.py` updates; Track **C** WIP — `0012_signal_snapshot_pi9_contract.py`, ORM `trace_id` + `signals` JSONB, `SIGNAL_PERSISTENCE_REPORT.md` (§8).

---

## 2. Migration State @ `0011_observation_validation_rejected`

### 2.1 Alembic head @ commit

| Check | Result | Evidence |
|-------|--------|----------|
| Single head | **`0011_observation_rejected`** | `tests/unit/test_alembic_revision_chain.py` @ `e9fa355` |
| Linear chain | `0001` → `0011` (11 revisions) | Same test file |
| PI8 lifecycle enum | `rejected` on `observation_validation_status` | `0011_observation_validation_rejected.py` |

### 2.2 Revision `0011_observation_validation_rejected` (PI8 Track A)

| Field | Value |
|-------|-------|
| File | `backend/app/persistence/migrations/versions/0011_observation_validation_rejected.py` |
| `down_revision` | `0010_observation_partitions_backfill` |
| Change | `ALTER TYPE observation_validation_status ADD VALUE IF NOT EXISTS 'rejected'` |
| Purpose | QA failure lifecycle; `received` remains draft/pending ingest state |

### 2.3 E-03 / signal-relevant chain

| Revision | File | PI9 relevance |
|----------|------|---------------|
| `0005` | `0005_observations_partitioned.py` | `price_observation`, `arrival_observation` (partitioned) |
| **`0006`** | **`0006_signals_partitioned.py`** | **`structured_signal`**, **`signal_snapshot`** (E-01-S05) |
| `0009` | `0009_weather_observations.py` | `weather_observation` |
| `0010` | `0010_observation_partitions_backfill.py` | Observation partition backfill |
| `0011` | `0011_observation_validation_rejected.py` | Head @ audit; `rejected` validation status |

---

## 3. Signal Schema @ `0006` (E-01-S05)

### 3.1 `structured_signal`

| Column | Notes |
|--------|-------|
| `signal_id`, `as_of_date` | Composite PK; monthly RANGE partition |
| `agent_type`, `commodity_id`, `registry_id` | FK to `commodity`, `commodity_registry` |
| `value`, `direction`, `magnitude`, `confidence` | TDS-006 signal fields |
| `signal_components`, `source_observation_refs` | JSONB |
| `agent_version` | Optional semver |

**Unique:** `(commodity_id, as_of_date, agent_type, registry_id)`

### 3.2 `signal_snapshot` @ `e9fa355`

| Column | Notes |
|--------|-------|
| `snapshot_id` | UUID PK |
| `commodity_id`, `as_of_date`, `registry_id` | Snapshot scope |
| `signal_ids` | JSONB array of `structured_signal` IDs |
| `snapshot_hash` | SHA-256 over canonical payload |
| `data_quality_snapshot_id` | Optional FK to DQS row |
| `created_at` | Append-only timestamp |

**PI9 Track C gap:** Charter asks for denormalized `signals` JSONB + `trace_id` on snapshot; working tree adds these via **`0012_signal_snapshot_pi9_contract.py`** (not in `e9fa355`) — see §8.

---

## 4. Observation & Weather Counts

### 4.1 Live DB @ 5433 (queried 2026-06-04)

```
alembic_version: 0011_observation_rejected

price_observation:     0
arrival_observation:   0
weather_observation:   0

commodity: 1 | region: 1 | market: 0 | commodity_registry: 0
data_quality_snapshot: 0
structured_signal: 0 | signal_snapshot: 0
```

### 4.2 PI8 committed evidence (use for planning when DB empty)

From [OBSERVATION_VALIDATION_REPORT.md](./OBSERVATION_VALIDATION_REPORT.md) and [PI8_EXECUTIVE_SUMMARY.md](./PI8_EXECUTIVE_SUMMARY.md):

| Table | `received` | `validated` | `rejected` |
|-------|------------|-------------|------------|
| `price_observation` | 0 | **60,445** | 0 |
| `arrival_observation` | 0 | **1,099** | 0 |
| **Total Agmarknet** | — | **61,544** | 0 |

| Weather | Count | Status |
|---------|-------|--------|
| NASA POWER (cotton belt) | **5,620** | All **`received`** (no PI8 batch promotion) |

| Coverage | Value |
|----------|-------|
| Belt mandis with price | **18 / 27** |
| TG primary basket | **4 / 4** |
| DQS Agmarknet-only | **0.8515** |
| DQS blended (Agmarknet + weather) | **0.7088** |

**Restore @5433 before PI9 signal integration gates:**

```bash
export DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra
# seed registry/markets, belt fixture backfill, observation_validate (PI8 reports document exact CLIs)
```

---

## 5. E-04 Story Gap

### 5.1 `docs/stories/`

| Epic file | Stories | E-04? |
|-----------|---------|-------|
| `E-00-Program-Foundation.md` | S01–S08 | No |
| `E-01-Data-Foundation.md` | S01–S11 | No (S05 = signal **schema** only) |
| `E-02-Commodity-Registry.md` | S01–S07 | References future E-04 orchestration only |
| **E-04** | **Missing** | — |

`docs/stories/README.md` indexes **E-00 through E-02 only**.

### 5.2 `docs/tds/` (frozen)

**TDS-014 § E-04 — Domain Agents:** F-04-01 Market … F-04-08 Orchestration graph; deps E-03; TDS-004/005; REQ-050–061.

### 5.3 PI9 charter (operational E-04 breakdown — not in `docs/stories/`)

| PI9 track | Story label | Deliverable |
|-----------|-------------|-------------|
| **A** | E-04-S01 Market Signal Runtime | `MarketSignalGenerator` → `StructuredSignal`; `E04_S01_COMPLETION_REPORT.md` |
| **B** | E-04-S02 Weather Signal Runtime | `WeatherSignalGenerator` → `StructuredSignal`; `E04_S02_COMPLETION_REPORT.md` |
| **C** | Signal snapshot persistence | `SIGNAL_PERSISTENCE_REPORT.md` |
| **D** | Replay harness | `SIGNAL_REPLAY_REPORT.md` |
| **E** | Signal quality | `SignalQualityService`; `SIGNAL_QUALITY_REPORT.md` |
| **F** | E-03 parallel | `E03_PARALLEL_STATUS.md` |
| **G** | Forecast readiness | `FORECAST_READINESS_ASSESSMENT.md` |
| **H** | Program status | `PI9_PROGRAM_STATUS.md` + `PI9_EXECUTIVE_SUMMARY.md` |

**Research specs (implementation contracts):** [SIGNAL_ENGINE_V1.md](../research/SIGNAL_ENGINE_V1.md), [SIGNAL_MATH_SPECIFICATION.md](../research/SIGNAL_MATH_SPECIFICATION.md), AC-01–AC-08 (LangGraph AC-06 — **out of PI9 stop rule**).

---

## 6. Agent / Signal Code Inventory — No Generators

### 6.1 `agents/` (package stubs only)

| Package | @ `e9fa355` |
|---------|-------------|
| `agents/market/` | Docstring only |
| `agents/weather/` | Docstring only |
| `agents/policy/`, `futures/`, `demand/`, `global_signals/` | Docstring only |
| `agents/orchestration/` | “LangGraph wiring in E-04” — **no graph** |

**Absent:** `MarketSignalGenerator`, `WeatherSignalGenerator`, LangGraph MI refresh graph.

### 6.2 `backend/` (persistence & stubs, no generators)

| Path | Role |
|------|------|
| `persistence/models/signal.py` | ORM `StructuredSignalModel`, `SignalSnapshotModel` |
| `persistence/repositories/signal.py` | Insert-only repos, `get_snapshot` |
| `persistence/validation/signal.py` | Bounds + agent_type validation |
| `persistence/migrations/versions/0006_signals_partitioned.py` | DDL |
| `services/mi_snapshot_materializer.py` | Redis MI from **existing** snapshot rows (E-01-S09) |
| `services/registry/mi_stub.py` | Loads `required_agents` only |
| `persistence/replay.py` | E-01 observation cutoff + replay **hash keys** — not signal generator replay |

**Absent under `backend/`:** `services/signals/`, agent orchestration, daily signal job, Policy/Futures/Global runtime.

### 6.3 `shared/`

| Path | Role |
|------|------|
| `shared/signal_contract/models.py` | Pydantic `StructuredSignal` stub |
| `shared/domain/enums.py` | `AgentType`, `Direction` |

### 6.4 Tests

| Area | Coverage |
|------|----------|
| `tests/unit/test_signals.py` | E-01-S05 persistence, hash, partitions |
| `tests/fixtures/data_foundation.py` | Manual 6-signal bundle inserts |
| `tests/replay/REPLAY_CHAIN.md` | Full chain doc; **no PI9 signal replay tests** |

**LangGraph:** pinned in `pyproject.toml` / `uv.lock`; **zero runtime imports** in application code.

### 6.5 Cotton registry (strict MI context)

`backend/app/persistence/seeds/fixtures/cotton.json`:

- `required_agents`: **Market, Futures**
- `optional_agents`: Weather, Policy, Demand, Global

PI9 implements **Market + Weather only** (enhanced degraded). **Futures still blocks strict MI** (DS-001).

---

## 7. PI9 Track Gaps (A–H)

| Track | Charter | @ `e9fa355` | Gap / next action |
|-------|---------|-------------|-------------------|
| **Audit** | `PI9_REPO_AUDIT.md` | **This document** | Baseline locked @ `e9fa355` |
| **A** | E-04-S01 `MarketSignalGenerator` (4 features) | **OPEN** | No generator; needs **validated** price/arrival + active registry; unit + integration tests |
| **B** | E-04-S02 `WeatherSignalGenerator` (4 features) | **OPEN** | No generator; B blocked on **validated** weather (F can promote 5,620 rows) |
| **C** | SignalSnapshot persistence + tests | **PARTIAL** | `0006` tables exist; charter fields (`signals`, `trace_id`) in **uncommitted** `0012` + ORM; `SIGNAL_PERSISTENCE_REPORT.md` |
| **D** | Signal replay harness | **OPEN** | Only E-01 `replay.py`; need same-input/same-output cycles for generators + `SIGNAL_REPLAY_REPORT.md` |
| **E** | `SignalQualityService` + dashboard report | **OPEN** | No service; no production signal rows to score |
| **F** | E-03 parallel (non-blocking) | **WIP (untracked)** | `E03_PARALLEL_STATUS.md`, weather validator, `.env.example` OGD steps — **not in `e9fa355`**; 9 empty mandis; `OGD_API_KEY` open |
| **G** | `FORECAST_READINESS_ASSESSMENT.md` | **OPEN** | Blocked on A–E outputs |
| **H** | `PI9_PROGRAM_STATUS.md` + executive summary | **OPEN** | After A–G |

**Inherited blockers (unchanged from PI8):** DS-001 unsigned (Futures); SR-01 live OGD; 9/27 fixture-empty mandis; LangGraph/orchestration deferred per PI9 stop rule.

---

## 8. Working Tree — Track C / F WIP (post-`e9fa355`)

Audit commit **`e9fa355` does not include** the following. If present locally, Tracks C/F are **in progress (uncommitted)**:

| Artifact | Typical path |
|----------|----------------|
| Migration | `backend/app/persistence/migrations/versions/0012_signal_snapshot_pi9_contract.py` |
| ORM delta | `trace_id` + `signals` JSONB on `SignalSnapshotModel` |
| Validation | `backend/app/persistence/validation/signal.py` (PI9 contract keys) |
| Tests | `tests/unit/test_signal_persistence_pi9.py` |
| Track F | `docs/reviews/E03_PARALLEL_STATUS.md`, `weather_observation_validation_service.py` |
| Report | `docs/reviews/SIGNAL_PERSISTENCE_REPORT.md` |

Do not treat PI9 Track C as **shipped** until `0012` is committed and `alembic upgrade head` passes in CI.

---

## 9. E-04 Readiness Gaps (Enhanced Degraded Start)

| # | Gap | Blocks |
|---|-----|--------|
| 1 | **No E-04 story files** in `docs/stories/` | Sprint traceability; only PI9/KDO + TDS-014 |
| 2 | **No signal generators** | Tracks A, B; success criteria 1–2 |
| 3 | **No SignalSnapshot assembly service** | Track C; success criterion 3 |
| 4 | **No signal replay proof** | Track D; success criterion 4 |
| 5 | **@5433 DB empty** | Any integration proof of PI8 counts |
| 6 | **Weather still `received`** (per PI8/F docs) | Track B “validated weather only”; run F’s `--include-weather` after reload |
| 7 | **`agents/*` + LangGraph AC-06** | Full E-04 orchestration (explicitly out of PI9 scope) |
| 8 | **Futures agent + DS-001** | Strict MI / production (not PI9 scope) |

**Ready today:** E-01 signal DDL, repos, validation, research specs, PI8 input-readiness recheck, observation validation service (Agmarknet).

---

## 10. Recommended Track Order

KDO critical path:

```mermaid
flowchart LR
  AUD[Repo audit] --> C[C Persistence]
  C --> A[A Market]
  C --> B[B Weather]
  A --> D[D Replay]
  B --> D
  A --> E[E Quality]
  B --> E
  D --> G[G Forecast readiness]
  E --> G
  G --> H[H Program status]
  F[F E-03 parallel]
```

| Wave | Tracks | Notes |
|------|--------|-------|
| **0** | Reload @5433 corpus (ops) | Parallel to audit; required for integration gates |
| **1** | **Audit** · **C** · **F** (parallel, non-blocking) | C before A∥B |
| **2** | **A ∥ B** | After C repos/migration stable |
| **3** | **D ∥ E** | After first signals exist |
| **4** | **G → H** | Forecast readiness + `PI9_EXECUTIVE_SUMMARY.md` |

**Order:** **Audit → C → A∥B → D∥E → G → H**; **F** anytime (non-blocking to E-04).

**Do not start @ PI9:** Forecast engine, decision engine, recommendation engine, LLM agents (per stop rule).

---

## 11. Top 5 PI9 Blockers

| Rank | Blocker | Impact | Primary track |
|------|---------|--------|---------------|
| **1** | **@5433 DB empty** — PI8 corpus not loaded | No integration proof for generators or replay | Ops / Wave 0 |
| **2** | **No signal generators** — `MarketSignalGenerator`, `WeatherSignalGenerator` absent | PI9 success criteria 1–2 blocked | **A**, **B** |
| **3** | **No SignalSnapshot assembly + PI9 contract** | Cannot persist denormalized signal bundles | **C** |
| **4** | **No E-04 stories in `docs/stories/`** | Traceability gap vs TDS-014 | Governance |
| **5** | **Weather rows `received`** (5,620 per PI8) | Weather generator should consume validated rows only | **F** → **B** |

**Secondary:** DS-001 unsigned (strict MI); 9/27 fixture-empty mandis (SR-01); LangGraph orchestration deferred.

---

## 12. Quality Gates @ Audit Baseline

| Gate | @ `e9fa355` / disk |
|------|-------------------|
| `test_alembic_revision_chain_linear` | Expects head **`0011_observation_rejected`** |
| `pytest` without DB | Per PI8 merge: **137 passed** (docs) |
| `pytest` + `DATABASE_URL` @ 5433 | PI8: **196 passed** when corpus loaded; **empty DB ≠ PI8 state** |
| `alembic upgrade head` @ 5433 | **Pass** → `0011` |
| Signal generation deterministic | **Not met** |
| Replay validation | **Not met** |

---

## 13. Return Payload

| Field | Value |
|-------|-------|
| **Audit path** | `docs/reviews/PI9_REPO_AUDIT.md` |
| **Migration head** | **`0011_observation_rejected`** (repo + @5433) |
| **Obs @ 5433 (live)** | price **0**, arrival **0** |
| **Obs (PI8 docs)** | **61,544 validated** (60,445 price + 1,099 arrival) |
| **Weather @ 5433 (live)** | **0** |
| **Weather (PI8 docs)** | **5,620** (`received`) |
| **Signal rows @ 5433** | **0** / **0** |
| **E-04 stories** | **None** in `docs/stories/`; **TDS-014** + PI9 E-04-S01/S02 charter |
| **E-04 readiness** | Schema **yes**; runtime **no**; DB corpus **not loaded** @5433 |
| **Recommended order** | **Audit → C → A∥B → D∥E → G → H**; **F** anytime |

---

## 14. References

| Resource | Path |
|----------|------|
| PI8 executive summary | [PI8_EXECUTIVE_SUMMARY.md](./PI8_EXECUTIVE_SUMMARY.md) |
| Observation validation | [OBSERVATION_VALIDATION_REPORT.md](./OBSERVATION_VALIDATION_REPORT.md) |
| Weather activation | [WEATHER_ACTIVATION_REPORT.md](./WEATHER_ACTIVATION_REPORT.md) |
| Signal readiness recheck | [SIGNAL_READINESS_RECHECK.md](../research/SIGNAL_READINESS_RECHECK.md) |
| Signal engine spec | [SIGNAL_ENGINE_V1.md](../research/SIGNAL_ENGINE_V1.md) |
| Migration `0011` | `backend/app/persistence/migrations/versions/0011_observation_validation_rejected.py` |
| Migration `0006` | `backend/app/persistence/migrations/versions/0006_signals_partitioned.py` |
| Cotton seed | `backend/app/persistence/seeds/fixtures/cotton.json` |

---

*End of PI9 repository audit — baseline @ `e9fa355`.*
