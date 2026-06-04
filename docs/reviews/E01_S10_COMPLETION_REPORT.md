# E-01-S10 Completion Report — CommodityRegistry

**Date:** 2026-06-04  
**Story:** E-01-S10 — CommodityRegistry Table (Schema Only)  
**Epic:** E-01 Data Foundation  
**Migration:** `0003_commodity_registry`

---

## Summary

Implemented versioned `commodity_registry` table per TDS-006 §3.3 and ADR-003 extensions: `required_agents`, `optional_agents`, `signal_weights`, `regime_priority`, `decision_rules` JSONB, semver `version`, `effective_from`/`effective_to`, `is_active`, and default `forecast_horizons` `[30, 60, 90]`. Partial unique index enforces exactly one active row per `commodity_id`. ORM, repository, validation, and `RegistryService.get_active_config()` deliver ADR-003 read pattern.

---

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| AC-1 | Table with ADR-003 architecture review fields | **Done** | `0003_commodity_registry.py`, `models/registry.py` |
| AC-2 | Partial UNIQUE one `is_active=true` per `commodity_id` | **Done** | `ix_registry_commodity_active`; `test_single_active_registry` |
| AC-3 | `decision_rules` includes msp_proximity_pct, default_partial_sell_pct, formula_version | **Done** | Validation in `validation/registry.py` |
| AC-4 | `forecast_horizons` default [30,60,90] | **Done** | Server default in migration + `DEFAULT_FORECAST_HORIZONS` |
| AC-5 | Version semver + effective_from / effective_to | **Done** | Columns on model and migration |

---

## Deliverables

| Artifact | Path |
|----------|------|
| Migration | `backend/app/persistence/migrations/versions/0003_commodity_registry.py` |
| ORM | `backend/app/persistence/models/registry.py` |
| Repository | `backend/app/persistence/repositories/registry.py` |
| Validation | `backend/app/persistence/validation/registry.py` |
| Service | `backend/app/persistence/services/registry_service.py` |
| UoW wiring | `backend/app/persistence/unit_of_work.py` |

---

## ADR-003 Compliance

| Rule | Implementation |
|------|----------------|
| required/optional agents split (not sole `minimum_agents`) | `required_agents`, `optional_agents` JSONB columns |
| Exactly one active per commodity | Partial unique index + `activate_version()` |
| Activation swap in transaction | `CommodityRegistryRepository.activate_version()` |
| Downstream read via `RegistryService.get_active_config()` | `services/registry_service.py` |
| decision_rules keys | Validated on insert/activation |

---

## Tests

| Test | Type | Status |
|------|------|--------|
| `test_required_agents_json_schema_rejects_empty` | Unit | Pass |
| `test_required_agents_json_schema_rejects_invalid_agent` | Unit | Pass |
| `test_single_active_registry` | Integration | Skip without `DATABASE_URL` |
| `test_version_activation` | Integration | Skip without `DATABASE_URL` |
| `test_registry_service_raises_when_no_active` | Integration | Skip without `DATABASE_URL` |

---

## E-02 Readiness

Schema supports TDS-009 §11.1 cotton YAML excerpt (required/optional agents, signal_weights, regime_priority, decision rule params) without further migration. Cotton seed is E-02 scope.

---

## Quality Gates

| Check | Result |
|-------|--------|
| `uv run ruff check .` | Pass |
| `uv run mypy` | Pass |
| `uv run pytest tests/ -v` | Pass (unit); integration requires `DATABASE_URL` |
| `alembic upgrade head` | Not run locally — no `.env`; docker Postgres credentials mismatch |

---

*End of E-01-S10 completion report.*
