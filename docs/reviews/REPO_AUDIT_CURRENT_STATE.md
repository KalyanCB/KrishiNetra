# Repository Audit — Current State (PI1 Phase 0)

| Field | Value |
|-------|-------|
| **Date** | 2026-06-03 |
| **Auditor** | KDO PI1 orchestration |
| **HEAD** | `30583fc` — E-00 M0 + E-01 Phase 1 foundation |
| **Remote** | https://github.com/KalyanCB/KrishiNetra (`main`) |
| **Frozen scope** | No edits to `docs/founder`, `docs/tds`, founder decisions, or architecture |

---

## 1. Validation commands (evidence)

| Command | Result | Notes |
|---------|--------|-------|
| `git log -1 --oneline` | `30583fc E-00 M0 + E-01 Phase 1 foundation` | Single commit bundles M0 + E-01 S01–S03 |
| `uv run pytest tests/ -v` | **28 passed**, **6 skipped**, 0 failed | Skips: `DATABASE_URL` not set in shell |
| `uv run ruff check .` | **PASS** | |
| `uv run mypy` | **PASS** | 68 source files, 0 errors |
| `uv run python scripts/check_imports.py` | **PASS** | ADR-001 boundaries |
| `./scripts/ci-local.sh` | **PASS** | Without `DATABASE_URL`; alembic step skipped locally |

### Local integration attempt (2026-06-03)

| Step | Result |
|------|--------|
| `docker compose -f docker-compose.dev.yml up -d postgres` | Container healthy |
| `DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5432/krishinetra` + `alembic upgrade head` | **FAIL** — `password authentication failed for user "krishinetra"` |
| Root cause (probable) | Host port `5432` bound by Docker; volume or competing Postgres instance may not match `.env.example` credentials |

**Implication:** DB-backed AC for S01/S03 are **not re-validated on this workstation**; GitHub Actions CI runs `alembic upgrade head` against service Postgres with matching credentials (`.github/workflows/ci.yml`).

---

## 2. Persistence inventory

| Area | Path | State |
|------|------|-------|
| Alembic config | `alembic.ini` | Present |
| Migrations | `backend/app/persistence/migrations/versions/` | `0001_alembic_bootstrap`, `0002_reference_entities` |
| ORM models | `backend/app/persistence/models/reference.py` | S03 reference entities only |
| Repositories | `base.py`, `reference.py` (Commodity stub) | S02 pattern + one stub repo |
| Shared contracts | `shared/persistence/contracts.py` | Immutability guard |
| Session / UoW | `database.py`, `unit_of_work.py`, `dependencies.get_db` | Present |
| Seeds | `seeds/runner.py` | Framework only; `apply()` → `NotImplementedError` (E-02) |
| **Not present** | `commodity_registry`, observations, signals, forecast, decision, Redis MI client | E-01-S04–S10 |

**Migration head:** `0002_reference_entities`

---

## 3. Story completion (evidence-based)

### E-00 — Program Foundation (M0)

| Story | Claimed (E00_PROGRAM_STATUS) | Verified | Health |
|-------|------------------------------|----------|--------|
| E-00-S01 | Done | Layout manifest + `test_repo_layout` | **GREEN** |
| E-00-S02 | Done | `uv.lock`, editable `shared`, `test_import_shared` | **GREEN** |
| E-00-S03 | Done | `/health`, `/v1/*` stubs, `test_api_shell` | **GREEN** |
| E-00-S04 | Done | `.github/workflows/ci.yml`, `ci-local.sh` | **GREEN** |
| E-00-S05 | Done | `check_imports.py`, boundary tests | **GREEN** |
| E-00-S06 | Done | `docker-compose.dev.yml`, `.env.example`, integration test (skip w/o env) | **YELLOW** — local DB auth not verified here |
| E-00-S07 | Done | `trace_id` middleware + unit tests | **GREEN** |
| E-00-S08 | Done | `shared/domain`, `signal_contract`, mypy strict on shared | **GREEN** |

**Epic E-00 verdict:** **Complete** for M0 gates (unit CI green). Local full-stack verify is **YELLOW** until `.env` + working Postgres on 5432.

---

### E-01 — Data Foundation (partial epic)

| Story | E01_PROGRAM_STATUS claim | On-disk evidence | Health |
|-------|--------------------------|------------------|--------|
| **E-01-S01** | 100% | Alembic tree, `0001` bootstrap, CI migration job, `test_alembic_revision_chain`, integration tests | **GREEN** (code); **YELLOW** (local DB run) |
| **E-01-S02** | 100% | `REPOSITORY_PATTERN.md`, `BaseRepository`, `ImmutableVersionRepository`, `test_repository_immutability` (stub model) | **GREEN** |
| **E-01-S03** | 100% | `0002` DDL + ORM + `test_reference_entities` (3 tests, skip w/o DB) | **GREEN** (code); **YELLOW** (integration not run locally) |
| E-01-S04 | Not started | No `price_observation` / `arrival_observation` | **RED** (not started) |
| E-01-S05 | Not started | No signal tables | **RED** |
| E-01-S06 | Not started | No forecast tables | **RED** |
| E-01-S07 | Not started | No decision stack | **RED** |
| E-01-S08 | Not started | No `data_quality_snapshot` | **RED** |
| E-01-S09 | Not started | No Redis MI client in `backend/` | **RED** |
| E-01-S10 | Not started | No `commodity_registry` migration | **RED** — **blocks E-02-S02+** |
| E-01-S11 | Not started | No full FK integration fixture | **RED** |

**Do not assume E-01 complete.** Phase 1 stop delivered **S01–S03 only** (~27% of epic stories by count; foundation slice only).

---

### E-02 — Commodity Registry

| Story | State | Health |
|-------|-------|--------|
| E-02-S01 – S07 | No implementation (forbidden this PI) | **RED** (not started) — readiness doc only |

---

## 4. Claimed vs actual (E01_PROGRAM_STATUS.md)

| Claim | Audit finding |
|-------|---------------|
| S01–S03 100% Green | **Supported** by code, unit tests, CI workflow design |
| Phase 1 workstreams A–F complete | **Supported** for docs (S04–S07 readiness, DS-001, governance reports exist) |
| `28 passed, 6 skipped` | **Reproduced** on 2026-06-03 |
| E-02 unblock: S03 done; S10 required | **Accurate** — no `commodity_registry` table |
| Overall GREEN | **Partially agree** — **YELLOW** for integration evidence on developer machine |

---

## 5. Architecture / ADR deviations

| Area | Expected | Actual | Severity |
|------|----------|--------|----------|
| ADR-001 import boundaries | Enforced in CI | `check_imports.py` passes | None |
| ADR-002 Alembic location | `backend/app/persistence/migrations/` | Matches | None |
| ADR-002 empty bootstrap | No business tables in `0001` | `0001` empty; tables in `0002` | None — S03 bundled in same phase |
| ADR-003 registry versioning | `commodity_registry` + partial unique active | **Not implemented** (S10) | Planned gap |
| TDS-006 §3.1–3.5 reference entities | String PKs, JSONB profile fields | Matches `reference.py` / `0002` | None |
| TDS-006 ER: Registry scopes Region | Diagram shows Registry→Region | Implementation: Region→Commodity only (S03) | **Acceptable** — registry table absent until S10 |
| E-01-S02 immutability test | Real `ForecastVersion` | Stub table in unit test | **Low** — acceptable until S06 |
| Seed data | No cotton in E-01 | `SeedRunner.apply` not implemented | Per story scope |
| Forbidden packages | No forecast/decision/agent/MI code | Stubs only under package dirs | Compliant |

---

## 6. Health summary by area

| Area | Health | Rationale |
|------|--------|-----------|
| Repo layout / M0 | **GREEN** | E-00 stories evidenced in tests + CI |
| Tooling (ruff/mypy/imports) | **GREEN** | All pass |
| Unit tests | **GREEN** | 28/28 executed pass |
| Integration / DB | **YELLOW** | 6 skips; local Postgres auth failure |
| E-01 S01–S03 code | **GREEN** | Delivered and aligned to ADR-002 / TDS-006 §3.1–3.5 |
| E-01 S04–S11 | **RED** | Not started |
| E-02 | **RED** | Not started (docs-only this PI) |
| Research (DS-001, cotton validation) | **GREEN** | Docs present; founder sign-off pending |
| CI on GitHub | **GREEN** (expected) | Workflow includes Postgres + `alembic upgrade head` |

---

## 7. Existing implementation docs (reference)

| Path | Role |
|------|------|
| `docs/implementation/E01_PROGRAM_STATUS.md` | Phase 1 status (S03 stop) |
| `docs/implementation/E01_S01/02/03_REPORT.md` | Per-story evidence |
| `docs/implementation/E01_NEXT_PHASE_READINESS.md` | S04–S07 planning |
| `docs/reviews/E01_GOVERNANCE_AUDIT.md` | Phase 1 governance |
| `docs/reviews/E01_PHASE1_COMPLETION_REPORT.md` | Completion narrative |
| `docs/research/DS001_FUTURES_VENDOR_DECISION.md` | Futures vendor |
| `docs/research/COTTON_DATA_SOURCE_VALIDATION.md` | Public source validation |

---

## 8. Audit verdict

**Phase 0:** Repository matches **E-00 complete** and **E-01-S01–S03 complete** at code level. **E-01 epic is not complete.** Local integration validation is **inconclusive** (environment); rely on CI Postgres for migration/FK proof until dev stack credentials are fixed.

**Next code gate (post-PI1):** E-01-S10 (`commodity_registry`) before E-02 implementation; then S04–S08 per `E01_EXECUTION_PLAN.md`.
