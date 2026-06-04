# E-02 Completion Report — Commodity Registry

**Date:** 2026-06-04  
**Epic:** E-02 — Commodity Registry  
**PI:** PI4 Track A  
**Prerequisites:** E-01 complete @ migration `0008_decision_stack`  
**Architecture:** Frozen (ADR-003)

---

## Summary

Delivered cotton `Commodity` + `CommodityProfile`, versioned `CommodityRegistry` v1.0.0 (active), Telangana region/market hierarchy seed, public read APIs, internal ops activation API, and `RegistryService.get_active_config()` with 5-minute in-memory cache — unblocking E-03 source mappings and E-04 agent orchestration stub.

---

## Stories Completed

| Story | Title | Status |
|-------|-------|--------|
| E-02-S01 | Commodity and CommodityProfile Service (Cotton) | **Done** |
| E-02-S02 | CommodityRegistry Versioning and Activation | **Done** |
| E-02-S03 | Registry Config Validation (Agents and Weights) | **Done** |
| E-02-S04 | Cotton Registry v1.0.0 Seed (Active) | **Done** |
| E-02-S05 | Public Registry Read APIs | **Done** |
| E-02-S06 | Internal Registry Activation API (Ops) | **Done** |
| E-02-S07 | Registry Service Integration with MI Pipeline Stub | **Done** |

---

## Acceptance Criteria Evidence

### E-02-S01

| AC | Evidence |
|----|----------|
| AC-1 | `cotton.json` + `SeedRunner`: `status=active`, `reference_implementation_flag=true` |
| AC-2 | Profile: display_name, unit=quintal, currency=INR, quality_dimensions |
| AC-3 | Six participant roles in fixture and seed |
| AC-4 | `phase_1_active_roles` = Farmer, Trader |
| AC-5 | `test_seed_idempotent` — second run does not duplicate registry row |

### E-02-S02

| AC | Evidence |
|----|----------|
| AC-1 | `RegistryService.create_registry_version` inserts `is_active=false` |
| AC-2 | `activate_registry_version` swaps active; prior deactivated |
| AC-3 | `get_active_registry` / `get_active_config` raises when missing |
| AC-4 | `effective_from` required; `effective_to` set on superseded version |
| AC-5 | `emit_registry_version_activated` audit log + `REGISTRY_VERSION_ACTIVATED` event type |

### E-02-S03

| AC | Evidence |
|----|----------|
| AC-1–AC-6 | `validation/registry.py` + `test_registry_validation.py` |

### E-02-S04

| AC | Evidence |
|----|----------|
| AC-1–AC-7 | `fixtures/cotton.json` TDS-009 §11.1 values; `test_cotton_seed_active_registry` |

### E-02-S05

| AC | Evidence |
|----|----------|
| AC-1–AC-6 | `GET /v1/commodities`, `GET /v1/commodities/cotton/registry/active`; contract tests |

### E-02-S06

| AC | Evidence |
|----|----------|
| AC-1–AC-5 | Internal POST routes with `X-API-Key`; `test_internal_registry_requires_api_key` |

### E-02-S07

| AC | Evidence |
|----|----------|
| AC-1–AC-5 | Import `backend.app.services.registry`; cache TTL 300s; `mi_stub.load_required_agents` |

---

## Deliverables

| Artifact | Path |
|----------|------|
| Registry service | `backend/app/services/registry/` |
| Cotton config constants | `backend/app/services/registry/cotton_config.py` |
| Seed fixture | `backend/app/persistence/seeds/fixtures/cotton.json` |
| Seed runner | `backend/app/persistence/seeds/runner.py` |
| Bootstrap script | `scripts/seed_cotton_baseline.py` |
| Public + internal API | `backend/app/api/v1/registry.py` |
| Extended validation | `backend/app/persistence/validation/registry.py` |
| Reference repos | `backend/app/persistence/repositories/reference.py` |
| ParticipantRole enum | `shared/domain/enums.py` |

---

## Cotton v1.0.0 Registry (TDS-009 §11.1)

| Field | Value |
|-------|-------|
| `version` | 1.0.0 |
| `required_agents` | Market, Futures |
| `optional_agents` | Weather, Policy, Demand, Global |
| `signal_weights` | Futures 0.25, Market 0.22, Policy 0.15, Demand 0.15, Weather 0.13, Global 0.10 |
| `regime_priority` | DATA_DEGRADED → NORMAL (6 regimes) |
| `decision_rules` | msp_proximity_pct 0.03, default_partial_sell_pct 0.50, formula_version 1.0.0 |
| `weather_variables` | rainfall, humidity, **acreage** |

---

## Telangana Region/Market Seed

| Type | IDs |
|------|-----|
| State | `reg_tg_state` (Telangana) |
| Mandi regions | `reg_tg_khammam`, `reg_tg_warangal`, `reg_tg_karimnagar`, `reg_tg_kesamudram` |
| Markets | `mkt_tg_khammam_apmc`, `mkt_tg_warangal`, `mkt_tg_karimnagar`, `mkt_tg_kesamudram` |

All markets include `source_identifiers.agmarknet` for E-03 ingest mapping.

---

## Migration Changes

**None.** E-02 uses existing schema from E-01 (`0002` reference entities, `0003` commodity_registry). Head remains `0008_decision_stack`.

---

## Tests

| File | Tests | Type |
|------|-------|------|
| `tests/unit/test_registry_validation.py` | 7 | Unit |
| `tests/unit/test_seed_framework.py` | 4 | Unit |
| `tests/integration/test_cotton_registry.py` | 9 | Integration |
| `tests/unit/test_registry_api.py` | 5 | Unit + integration |
| `tests/unit/test_commodity_registry.py` | +3 new (historical, audit, cache) | Integration |
| **E-02 new/extended total** | **28** | — |

**Unit run (no DATABASE_URL):** 62 passed, 41 skipped (integration), 0 failed  
**Integration:** Requires `DATABASE_URL` + `alembic upgrade head` + seed

### Story test mapping

| Story requirement | Test |
|-------------------|------|
| `test_cotton_commodity_active` | ✓ |
| `test_participant_roles_six` | ✓ |
| `test_phase_1_active_subset` | ✓ |
| `test_single_active_registry` | ✓ (E-01, retained) |
| `test_historical_registry_readable` | ✓ |
| `test_activation_audit_log` | ✓ |
| `test_weights_sum_to_one` | ✓ |
| `test_required_agents_disjoint_optional` | ✓ |
| `test_cotton_decision_rules_defaults` | ✓ |
| `test_cotton_seed_active_registry` | ✓ |
| `test_registry_fixture_snapshot` | ✓ |
| `test_get_commodities_contract` | ✓ |
| `test_get_active_registry_contract` | ✓ |
| `test_registry_public_anonymous` | ✓ |
| `test_internal_registry_requires_api_key` | ✓ |
| `test_activate_registry_swaps_active` | ✓ |
| `test_registry_service_cotton` | ✓ |
| `test_registry_cache_invalidation` | ✓ |

---

## Quality Gates

| Check | Result |
|-------|--------|
| `uv run ruff check .` | Pass |
| `uv run mypy` | Pass (106 files) |
| `uv run pytest tests/` | Pass (unit); integration skipped without Postgres |
| `alembic upgrade head` | No new migration; head `0008_decision_stack` |

---

## E-03 Handoff

Import path for downstream teams:

```python
from backend.app.services.registry import RegistryService, RegistryNotFoundError
```

Active cotton registry exposes `price_sources`, `arrival_sources`, `weather_variables`, `policy_drivers` as string arrays for ingest mapping.

Bootstrap after migrations:

```bash
uv run alembic upgrade head
uv run python scripts/seed_cotton_baseline.py
```

---

## Out of Scope (Confirmed)

- E-03 ingest pipelines
- Signal runtime
- Forecast/decision logic
- PI4 research docs (B–G) and `PI4_PROGRAM_STATUS`

---

## Rollback Note

Per E-02 seed plan: deactivate registry version (set `is_active=false`), do not DELETE historical rows (ADR-003).

---

*End of E-02 completion report.*
