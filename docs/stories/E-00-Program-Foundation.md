# E-00 — Program Foundation

| Field | Value |
|-------|-------|
| **Epic ID** | E-00 |
| **Goal** | Monorepo, CI, local dev, logging/trace conventions — engineering ready (M0) |
| **TDS** | TDS-013 |
| **REQ** | REQ-120 |
| **Milestone** | M0 |
| **Sprint** | Sprint 0 |

## Feature Map

| Feature ID | Stories |
|------------|---------|
| F-00-01 Repo scaffold | E-00-S01, E-00-S02, E-00-S03 |
| F-00-02 CI gates | E-00-S04, E-00-S05 |
| F-00-03 Local dev | E-00-S06 |
| F-00-04 Trace_id / logging | E-00-S07 |

---

## E-00-S01 — Monorepo Directory Scaffold

### Summary

Create the KrishiNetra monorepo directory tree per TDS-013 §2 without application business logic.

### Dependencies

| Dependency | Type |
|------------|------|
| None | — |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | All top-level paths exist: `backend/`, `agents/`, `forecasting/`, `decision_engine/`, `market_intelligence/`, `shared/`, `frontend/`, `docs/`, `infra/`, `tests/`, `scripts/` |
| AC-2 | Each Python package contains `__init__.py` and matches TDS-013 module names |
| AC-3 | `agents/explainability/` is the only path designated for future LLM SDK imports |
| AC-4 | `infra/README.md` states Wave 4+ for Terraform/Docker production (no prod IaC in this story) |
| AC-5 | Root `README.md` links to `docs/founder/`, `docs/tds/`, `docs/stories/` |

### Definition of Done

- [ ] Directory tree merged to `main`
- [ ] No application code beyond package stubs and READMEs
- [ ] Peer review confirms alignment with TDS-013 §2 diagram

### Technical Notes

- Follow exact paths in TDS-013; do not add `inventory/` persistence (Phase 2, TDS-013 §10)
- `backend/app/api/v1/` placeholder modules may be empty `.py` files
- Reference: [TDS-013](../tds/TDS-013-Repository-Architecture.md) §2

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_repo_layout` | Script or pytest collects expected paths from manifest; fails if missing |
| CI | Layout check runs on PR (no unit tests required for empty packages) |

### Traceability

REQ-120 | TDS-013 | ADR-001

---

## E-00-S02 — Python Workspace and Dependency Management

### Summary

Configure Python 3.11+ workspace with lockfile and editable installs for `backend`, `shared`, and domain packages.

### Dependencies

| Dependency | Type |
|------------|------|
| E-00-S01 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Single root `pyproject.toml` (or workspace config per ADR-004) declares Python `>=3.11` |
| AC-2 | Lockfile committed (`uv.lock` or `poetry.lock`) |
| AC-3 | Editable install allows `from shared.domain import ...` from `backend` tests |
| AC-4 | Core deps declared: `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `alembic`, `redis`, `httpx` (dev: `pytest`, `ruff`, `mypy`) |
| AC-5 | No LLM SDK packages in root/default dependency group |

### Definition of Done

- [ ] `pip install -e .` or `uv sync` succeeds on clean machine
- [ ] Documented in `backend/README.md` (one-command setup)
- [ ] ADR-004 records package manager choice

### Technical Notes

- LangGraph dependency may be declared but not used until E-04
- Pin versions for reproducibility (TDS-013 determinism theme)
- Reference: [ADR-004](../adrs/ADR-004-local-development-stack.md)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_import_shared` | Import `shared` package in pytest smoke test |
| CI | Install job verifies lockfile sync on PR |

### Traceability

TDS-013 §1, §5 | ADR-004

---

## E-00-S03 — FastAPI Application Shell

### Summary

Bootstrappable FastAPI app with health check and API v1 router mount points (empty handlers).

### Dependencies

| Dependency | Type |
|------------|------|
| E-00-S02 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `backend/app/main.py` exposes ASGI app factory |
| AC-2 | `GET /health` returns `200` with `{ "status": "ok" }` |
| AC-3 | `backend/app/api/v1/` router mounted at `/v1` with sub-routers: `market_intelligence`, `decisions`, `conversation`, `outcomes`, `registry` (stubs return `501` or empty) |
| AC-4 | App starts via documented command (`uvicorn backend.app.main:app`) |
| AC-5 | OpenAPI schema generated at `/docs` (stub routes acceptable) |

### Definition of Done

- [ ] Health endpoint verified locally
- [ ] No business logic in handlers
- [ ] Merged with passing CI from E-00-S04

### Technical Notes

- Structure matches TDS-010 API groups without implementing contracts yet
- Config from environment: `DATABASE_URL`, `REDIS_URL` optional for health-only
- Reference: [TDS-010](../tds/TDS-010-API-Architecture.md) §3, [TDS-003](../tds/TDS-003-Service-Architecture.md)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_health_endpoint` | `httpx` AsyncClient GET `/health` → 200 |
| `test_v1_mount` | Each v1 sub-router prefix responds (404/501 acceptable) |

### Traceability

REQ-120 | TDS-010 §3 | TDS-013 §2

---

## E-00-S04 — CI Pipeline (Lint, Format, Unit Smoke)

### Summary

GitHub Actions (or equivalent) workflow enforcing TDS-013 §7 CI gates for PRs.

### Dependencies

| Dependency | Type |
|------------|------|
| E-00-S02 | Blocks |
| E-00-S03 | Blocks (for API smoke test) |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Workflow runs on PR to `main`: Ruff lint + format check |
| AC-2 | Mypy runs on `shared/` (strict); other packages may use gradual typing initially |
| AC-3 | Pytest runs unit smoke tests (health, layout, import)
| AC-4 | Workflow fails on any lint/format/test failure |
| AC-5 | Status badge documented in root README (optional) |

### Definition of Done

- [ ] Green CI on sample PR
- [ ] Documented in `docs/stories/` or `backend/README.md` how to run locally same as CI

### Technical Notes

- Replay/backtest/nightly gates deferred until E-06/E-10 (TDS-013 §7.4)
- Secret scan: `gitleaks` or GitHub secret scanning (TDS-013 §7)
- Reference: [TDS-013](../tds/TDS-013-Repository-Architecture.md) §7

### Test Requirements

| Test | Requirement |
|------|-------------|
| CI self-test | Intentional failing PR rejected in dry run |
| Local parity | `scripts/ci-local.sh` mirrors workflow steps |

### Traceability

TDS-013 §6–§7

---

## E-00-S05 — Import Boundary Enforcement (CI)

### Summary

Automated check that forbidden imports (LLM in decision_engine, decision_engine in agents, etc.) fail CI.

### Dependencies

| Dependency | Type |
|------------|------|
| E-00-S01 | Blocks |
| E-00-S04 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Import rules encoded per TDS-013 §3.1 table |
| AC-2 | CI step fails if `decision_engine` imports `openai`, `anthropic`, or `langchain` |
| AC-3 | CI step fails if `agents/market` (etc.) imports `agents.explainability` |
| AC-4 | CI step fails if `forecasting` imports `decision_engine` |
| AC-5 | CI step fails if `shared` imports `backend`, `agents`, `forecasting`, or `decision_engine` |

### Definition of Done

- [ ] Negative fixture test proves detector catches violation
- [ ] Integrated into E-00-S04 workflow

### Technical Notes

- Implementation: `import-linter` contracts or custom AST script in `scripts/check_imports.py`
- Maps to FD-006, TC-001, TC-011
- Reference: [TDS-013](../tds/TDS-013-Repository-Architecture.md) §3.1, [ADR-001](../adrs/ADR-001-monorepo-module-boundaries.md)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_import_rules_pass` | Clean repo passes |
| `test_import_rules_fail_fixture` | Temporary forbidden import in `tests/fixtures/` triggers failure |

### Traceability

FD-006, TC-001 | TDS-013 §3.1 | REQ-015

---

## E-00-S06 — Local Development Environment

### Summary

Developers can run PostgreSQL and Redis locally and connect from the FastAPI app.

### Dependencies

| Dependency | Type |
|------------|------|
| E-00-S03 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `docker compose` (or documented equivalent) starts PostgreSQL 15+ and Redis 7+ |
| AC-2 | `.env.example` lists `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL` without secrets |
| AC-3 | App health check succeeds with DB/Redis optional; integration doc shows connection verify script |
| AC-4 | One-page setup in `backend/README.md` from clone to running health endpoint < 15 minutes |

### Definition of Done

- [ ] Verified on macOS and Linux (one platform minimum documented)
- [ ] No production credentials in repo

### Technical Notes

- Compose file lives in repo root or `infra/` as `docker-compose.dev.yml` (dev only, not prod IaC)
- Reference: [ADR-004](../adrs/ADR-004-local-development-stack.md)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `tests/integration/test_db_redis_connect` | Skip if env not set; passes when compose up |
| Manual | README checklist completed by second developer |

### Traceability

TDS-013 F-00-03 | ADR-004

---

## E-00-S07 — Structured Logging and trace_id Propagation

### Summary

JSON structured logs with `trace_id` on every HTTP request per TDS-013 §5.1 and TDS-010 §14.

### Dependencies

| Dependency | Type |
|------------|------|
| E-00-S03 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Middleware generates or accepts `X-Trace-Id` header; propagates to log context |
| AC-2 | Log format includes: `timestamp`, `level`, `trace_id`, `message`, `module` |
| AC-3 | Response includes `X-Trace-Id` echo header |
| AC-4 | No PII in default log fields |
| AC-5 | Logging configuration via environment (`LOG_LEVEL`) |

### Definition of Done

- [ ] Sample request produces parseable JSON log line with matching `trace_id`
- [ ] Documented for downstream epics (E-09 audit extends same id)

### Technical Notes

- Prepare for TDS-012 audit log correlation without implementing audit table (E-11)
- Reference: [TDS-010](../tds/TDS-010-API-Architecture.md) §14, [TDS-012](../tds/TDS-012-Security-Audit-Architecture.md) §6

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_trace_id_generated` | Request without header receives UUID trace_id |
| `test_trace_id_preserved` | Request with header preserves value in response |

### Traceability

TDS-013 F-00-04 | TDS-010 §14 | NFR-TRC-003 (prep)

---

## E-00-S08 — Shared Package Stubs (Domain, Contracts, Signal Contract)

### Summary

Initialize `shared/` with enums and Pydantic stubs aligned to TDS-006 and TDS-004 signal contract.

### Dependencies

| Dependency | Type |
|------------|------|
| E-00-S02 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `shared/domain/` defines enums: `AgentType`, `ActionType`, `PersonaType`, `LiquidityNeed`, `MarketRegime` (from TDS-009 taxonomy) |
| AC-2 | `shared/signal_contract/` defines `StructuredSignal` Pydantic model with fields: value, direction, magnitude, confidence, as_of_timestamp (REQ-060) |
| AC-3 | `shared/contracts/` placeholder module for API DTOs (empty OK) |
| AC-4 | Mypy strict passes on `shared/` |
| AC-5 | No imports from `backend`, `agents`, `forecasting`, `decision_engine` |

### Definition of Done

- [ ] Imported by E-00-S03 tests without circular deps
- [ ] Field names match TDS-006 attribute names (snake_case)

### Technical Notes

- `Direction` enum: bullish, bearish, neutral
- `AgentType`: Market, Weather, Policy, Demand, Futures, Global
- Do not add InventoryPosition model (Phase 2)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md), [TDS-004](../tds/TDS-004-Agent-Architecture.md) §3

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_structured_signal_validation` | Invalid confidence > 1 rejected |
| `test_enum_values_match_tds` | Snapshot test of enum member names |

### Traceability

REQ-060, REQ-090 | TDS-004 §3 | TDS-006

---

## Epic E-00 Definition of Done

| Gate | Condition |
|------|-----------|
| M0 complete | All E-00 stories Done |
| CI green | Lint, import boundaries, smoke tests on `main` |
| Onboarding | New developer runs local stack per README |
| E-01 unblocked | Database URL works against local PostgreSQL |

## Epic Dependencies (Outbound)

| Epic | Relationship |
|------|--------------|
| E-01 | Requires E-00 complete |

## Open Questions (Epic Level)

| ID | Item | Impact |
|----|------|--------|
| — | Package manager final sign-off | E-00-S02 (ADR-004) |

## Founder / Architecture Approvals

| Item | Status |
|------|--------|
| Monorepo layout | Frozen (TDS-013) |
| Import boundaries | Frozen (TDS-013, FD-006) |
