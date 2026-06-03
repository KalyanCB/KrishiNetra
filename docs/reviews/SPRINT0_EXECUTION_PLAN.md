# Sprint 0 Execution Plan — E-00 Program Foundation

**Date:** 2026-06-03  
**Milestone:** M0 — Engineering Ready  
**Gate:** Complete E-00-S01 → review → then S02–S08 sequentially

---

## Sprint Goal

Deliver a monorepo scaffold, CI-ready structure, local dev path, logging/trace conventions, and shared type stubs—**no business logic**.

---

## Execution Order

| Order | Story | Effort (est.) | Cumulative |
|-------|-------|---------------|------------|
| 1 | E-00-S01 | 0.5–1 d | Day 1 |
| 2 | E-00-S02 | 1 d | Day 2 |
| 3 | E-00-S03 | 1 d | Day 3 |
| 4 | E-00-S04 | 1 d | Day 4 |
| 5 | E-00-S05 | 0.5–1 d | Day 5 |
| 6 | E-00-S06 | 0.5 d | Day 5–6 |
| 7 | E-00-S07 | 0.5 d | Day 6 |
| 8 | E-00-S08 | 1 d | Day 7–8 |

**Total estimate:** 6–8 engineering days (one developer)

---

## E-00-S01 — Monorepo Directory Scaffold

### Inputs

- TDS-013 §2 directory tree
- ADR-001 import boundary paths
- Story E-00-S01 acceptance criteria

### Outputs

- Complete directory tree with Python `__init__.py` stubs
- `infra/README.md` (Wave 4+ prod IaC note)
- Root `README.md` with doc links
- `tests/unit/test_repo_layout.py` + layout manifest
- `backend/app/api/v1/*.py` empty stubs (no handlers)

### Files Expected (created)

```
README.md
infra/README.md
backend/app/__init__.py
backend/app/api/__init__.py
backend/app/api/v1/__init__.py
backend/app/api/v1/market_intelligence.py
backend/app/api/v1/decisions.py
backend/app/api/v1/conversation.py
backend/app/api/v1/outcomes.py
backend/app/api/v1/registry.py
backend/app/services/__init__.py
backend/app/events/__init__.py
backend/app/persistence/__init__.py
backend/app/config/__init__.py
agents/__init__.py + market|weather|policy|demand|futures|global_signals|orchestration/__init__.py
agents/explainability/__init__.py
agents/explainability/conversation/__init__.py
forecasting/__init__.py + features|models|calibration|backtest/__init__.py
decision_engine/__init__.py + rules|formulas|stability/__init__.py
market_intelligence/__init__.py + scoring|regime|snapshot/__init__.py
shared/__init__.py + domain|contracts|signal_contract|utils/__init__.py
frontend/src/.gitkeep (or package.json placeholder)
frontend/package.json (minimal placeholder)
tests/unit/__init__.py
tests/integration/__init__.py
tests/replay/__init__.py
tests/backtest/__init__.py
tests/fixtures/repo_layout_manifest.txt
scripts/.gitkeep
.github/workflows/ (empty or placeholder — full CI in S04)
```

**Explicitly NOT created:** `backend/app/main.py` (E-00-S03), `pyproject.toml` (E-00-S02), `inventory/` persistence (Phase 2)

### Risks

| Risk | Mitigation |
|------|------------|
| Path drift from TDS-013 | Manifest-driven test |
| Accidental business logic | Code review + empty stubs only |

### Validation Steps

1. Run `pytest tests/unit/test_repo_layout.py -v`
2. Manual `find` or tree compare against manifest
3. Verify `agents/explainability/` exists; no LLM code elsewhere
4. Read `infra/README.md` for Wave 4+ statement
5. Confirm root README links to docs/founder, docs/tds, docs/stories

### Estimated Effort

**0.5–1 day** (4–8 hours)

---

## E-00-S02 — Python Workspace and Dependency Management

### Inputs

- E-00-S01 tree
- ADR-004

### Outputs

- `backend/pyproject.toml` or root workspace config
- Lockfile
- `backend/README.md` setup section

### Files Expected

- `pyproject.toml`, lockfile, minimal `shared/` import test

### Risks

| Risk | Mitigation |
|------|------------|
| Wrong package root | Document editable installs |

### Validation

- `uv sync` or `poetry install` succeeds
- `pytest tests/unit/test_import_shared.py` (created in S02)

### Effort

**1 day**

---

## E-00-S03 — FastAPI Application Shell

### Inputs

- E-00-S02 workspace

### Outputs

- `backend/app/main.py`, health endpoint, v1 router stubs

### Validation

- `curl localhost:8000/health` → 200

### Effort

**1 day**

---

## E-00-S04 — CI Pipeline

### Inputs

- S02, S03

### Outputs

- `.github/workflows/ci.yml`

### Validation

- PR triggers green pipeline

### Effort

**1 day**

---

## E-00-S05 — Import Boundary Enforcement

### Inputs

- S01, S04

### Outputs

- `scripts/check_imports.py` or import-linter config

### Validation

- Forbidden import fails CI

### Effort

**0.5–1 day**

---

## E-00-S06 — Local Development Environment

### Inputs

- S03

### Outputs

- `docker-compose.dev.yml`, `.env.example`

### Validation

- `docker compose up` + health check

### Effort

**0.5 day**

---

## E-00-S07 — Structured Logging and trace_id

### Inputs

- S03

### Outputs

- Middleware in `backend/app/`

### Validation

- trace_id in logs and response header

### Effort

**0.5 day**

---

## E-00-S08 — Shared Package Stubs

### Inputs

- S02

### Outputs

- `shared/domain/`, `shared/signal_contract/` enums and models

### Validation

- mypy strict on shared/

### Effort

**1 day**

---

## Sprint 0 Exit Criteria (M0)

- [ ] All E-00 stories Done
- [ ] CI green on `main`
- [ ] New developer onboarding documented
- [ ] E-01 authorized to start

---

## Review Gate After S01

Before E-00-S02:

- [ ] Layout test passes
- [ ] No business logic in PR
- [ ] Lead review approval
