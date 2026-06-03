# E-00-S05 Report — Import Boundary Enforcement

**Story:** E-00-S05 | **Status:** Done | **Date:** 2026-06-03

## Acceptance criteria evidence

| AC | Evidence |
|----|----------|
| AC-1 | Rules encoded in `scripts/check_imports.py` per TDS-013 §3.1 |
| AC-2 | `decision_engine_no_llm` forbids `openai`, `anthropic`, `langchain*`, `langsmith` |
| AC-3 | `domain_agents_no_explainability` scans `agents/*` except `explainability` |
| AC-4 | `forecasting_no_decision_engine` blocks `decision_engine` imports |
| AC-5 | `shared_no_upward` blocks `backend`, `agents`, `forecasting`, `decision_engine`, `market_intelligence` |

## Implementation

- Checker: AST-based `scripts/check_imports.py` (ADR-001 alternative to import-linter)
- CI: step in `.github/workflows/ci.yml` and `scripts/ci-local.sh`
- Negative fixture: `tests/fixtures/import_violations/forbidden_explainability_import.py`
- Tests: `tests/unit/test_import_boundaries.py`

## Test results

```
uv run pytest tests/unit/test_import_boundaries.py -v  → 2 passed
uv run pytest tests/ -v                                → 20 passed, 1 skipped
./scripts/ci-local.sh                                  → Import boundaries OK
```

**ADR-005:** Layout manifest uses `agents/global_signals/`; checker does not reference deprecated `agents/global/` path.

## ADR / TDS compliance

- ADR-001: all four boundary classes enforced in CI
- TDS-013 §3.1: table rules mapped 1:1
- FD-006 / TC-001: deterministic/LLM separation guardrail in place

## Risks

- Dynamic imports (`importlib`) not detected at M0
