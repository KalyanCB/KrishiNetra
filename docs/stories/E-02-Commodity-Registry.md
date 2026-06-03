# E-02 — Commodity Registry

| Field | Value |
|-------|-------|
| **Epic ID** | E-02 |
| **Goal** | Cotton Commodity + Profile + active Registry v1 with required/optional agents, weights, six participant roles; public read APIs |
| **TDS** | TDS-006, TDS-009 §11–12, TDS-010 §10 |
| **REQ** | REQ-073, REQ-074, REQ-010 |
| **FD** | FD-001, FD-022, FD-008 |
| **Milestone** | M1 |
| **Sprint** | Sprint 1 |

## Feature Map

| Feature ID | Stories |
|------------|---------|
| F-02-01 Commodity+Profile | E-02-S01 |
| F-02-02 Registry versioning | E-02-S02, E-02-S03 |
| F-02-03 Cotton seed | E-02-S04 |
| F-02-04 Participant roles (6) | E-02-S01, E-02-S04 |
| F-02-05 Registry API | E-02-S05, E-02-S06 |

---

## E-02-S01 — Commodity and CommodityProfile Service (Cotton)

### Summary

Implement Commodity Registry Service domain logic for cotton `Commodity` + `CommodityProfile` records.

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S03 | Blocks (tables) |
| E-01-S02 | Blocks (repositories) |
| E-00-S08 | Blocks (shared types) |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Insert cotton: `commodity_id=cotton`, `status=active`, `reference_implementation_flag=true` (FD-001, REQ-074) |
| AC-2 | CommodityProfile: `display_name`, `unit=quintal`, `currency=INR`, quality_dimensions for cotton |
| AC-3 | `participant_roles_enabled` = [Farmer, Trader, Ginner, Miller, Exporter, Aggregator] (TDS-009 §12.1) |
| AC-4 | `phase_1_active_roles` = [Farmer, Trader] only |
| AC-5 | Idempotent seed script: second run does not duplicate |

### Definition of Done

- [ ] Cotton row exists after migration/seed command
- [ ] Repository tests pass
- [ ] Documented in `scripts/seed_cotton_baseline.py` (or equivalent)

### Technical Notes

- Service location: `backend/app/services/registry/` per TDS-013 §4
- Ginner/Miller/Exporter/Aggregator configured but **inactive** for Decision API validation until future phases
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §3.1–3.2, [TDS-009](../tds/TDS-009-Market-Intelligence-Framework.md) §12.1

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_cotton_commodity_active` | status active, reference flag true |
| `test_participant_roles_six` | len(participant_roles_enabled)==6 |
| `test_phase_1_active_subset` | phase_1_active_roles ⊆ participant_roles_enabled |

### Traceability

REQ-010, REQ-074 | FD-001, FD-022 | TDS-009 §12

---

## E-02-S02 — CommodityRegistry Versioning and Activation

### Summary

Implement versioned registry CRUD: create version, activate, deactivate prior, enforce single active per commodity.

### Dependencies

| Dependency | Type |
|------------|------|
| E-01-S10 | Blocks (commodity_registry table) |
| E-02-S01 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `create_registry_version(commodity_id, config)` inserts new row with `is_active=false` |
| AC-2 | `activate_registry_version(registry_id)` sets target active and deactivates previous active for same commodity |
| AC-3 | `get_active_registry(commodity_id)` returns exactly one or raises |
| AC-4 | `effective_from` required; `effective_to` set on superseded version |
| AC-5 | Emits conceptual `REGISTRY_VERSION_ACTIVATED` audit event (log + hook for E-11) |

### Definition of Done

- [ ] Unit tests cover activation swap
- [ ] ADR-003 behaviors implemented
- [ ] No retroactive mutation of historical registry rows

### Technical Notes

- Governance: ops-only activation (TDS-012 §10)—API in E-02-S06 internal only
- Agents and pipelines must read active version at runtime start (TDS-006 §5 replay step 1)
- Reference: [TDS-006](../tds/TDS-006-Data-Model.md) §3.3, [TDS-012](../tds/TDS-012-Security-Audit-Architecture.md) §10, [ADR-003](../adrs/ADR-003-commodity-registry-versioning.md)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_single_active_registry` | Activation enforces uniqueness |
| `test_historical_registry_readable` | Old version still fetchable by id |
| `test_activation_audit_log` | Mock audit sink receives event |

### Traceability

REQ-073 | FD-022 | TDS-012 §10

---

## E-02-S03 — Registry Config Validation (Agents and Weights)

### Summary

Validate registry payloads: `required_agents[]`, `optional_agents[]`, `signal_weights`, horizons, decision_rules.

### Dependencies

| Dependency | Type |
|------------|------|
| E-02-S02 | Blocks |
| E-00-S08 | Blocks (AgentType enum) |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `required_agents` and `optional_agents` disjoint; union ⊆ all AgentType values |
| AC-2 | `signal_weights` keys ⊆ required ∪ optional; weights sum to 1.0 ± 0.001 |
| AC-3 | `forecast_horizons` must include 30, 60, 90 (REQ-076) |
| AC-4 | `decision_rules.msp_proximity_pct` = 0.03 (founder clarification) |
| AC-5 | `decision_rules.default_partial_sell_pct` = 0.50 (founder clarification) |
| AC-6 | Reject registry missing any required_agents entry for cotton |

### Definition of Done

- [ ] Validator used on create_registry_version
- [ ] Invalid configs return structured validation errors

### Technical Notes

- Cotton required_agents: [Market, Futures] per TDS-009 §11.1
- Cotton optional: [Weather, Policy, Demand, Global]
- `formula_version` required string on registry (links to TDS-008)
- Reference: [TDS-009](../tds/TDS-009-Market-Intelligence-Framework.md) §4.1, §11.1

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_weights_sum_to_one` | Fail on 0.9 total |
| `test_required_agents_disjoint_optional` | Overlap fails |
| `test_cotton_decision_rules_defaults` | MSP 3%, partial 50% |

### Traceability

REQ-073, REQ-046, REQ-041 | FD-008 | TDS-009 §4, §11

---

## E-02-S04 — Cotton Registry v1.0.0 Seed (Active)

### Summary

Seed active cotton CommodityRegistry matching TDS-009 §11.1 reference YAML.

### Dependencies

| Dependency | Type |
|------------|------|
| E-02-S01 | Blocks |
| E-02-S02 | Blocks |
| E-02-S03 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Active registry `version=1.0.0` for cotton |
| AC-2 | `required_agents`: Market, Futures |
| AC-3 | `optional_agents`: Weather, Policy, Demand, Global |
| AC-4 | `signal_weights`: Futures 0.25, Market 0.22, Policy 0.15, Demand 0.15, Weather 0.13, Global 0.10 |
| AC-5 | `regime_priority`: [DATA_DEGRADED, MSP_FLOOR, CURVE_BACKWARDATION, TIGHT_SUPPLY, EXPORT_PUSH, NORMAL] |
| AC-6 | `price_sources`, `arrival_sources`, `policy_drivers`, `weather_variables` include acreage (Weather) |
| AC-7 | `formula_version` initial value documented (e.g. `1.0.0`) |

### Definition of Done

- [ ] `get_active_registry('cotton')` returns seeded config in dev/staging
- [ ] Seed runs as part of documented bootstrap after migrations
- [ ] E-03 ingestion can read source mappings from registry

### Technical Notes

- Source arrays reference REQ-070/071 source names (Agmarknet, eNAM, IMD, etc.)—strings only, no ingest yet
- Reference: [TDS-009](../tds/TDS-009-Market-Intelligence-Framework.md) §11.1, [TDS-007](../tds/TDS-007-Forecast-Architecture.md) §3

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_cotton_seed_active_registry` | Integration: active registry matches expected JSON fixture |
| `test_registry_fixture_snapshot` | Snapshot test of normalized config hash |

### Traceability

REQ-074, REQ-075 | FD-001 | TDS-009 §11

---

## E-02-S05 — Public Registry Read APIs

### Summary

Implement TDS-010 §10.1 and §10.2 public read endpoints.

### Dependencies

| Dependency | Type |
|------------|------|
| E-02-S04 | Blocks (seeded data) |
| E-00-S03 | Blocks (FastAPI shell) |
| E-00-S07 | Blocks (trace_id) |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `GET /v1/commodities` returns cotton with participant_roles_enabled (6) and phase_1_active_roles (2) |
| AC-2 | `GET /v1/commodities/cotton/registry/active` returns public subset per TDS-010 §10.2 |
| AC-3 | Response includes `required_agents`, `optional_agents`, `forecast_horizons`, `decision_rules_public` (msp 3%, partial 50%) |
| AC-4 | No auth required (anonymous tier TDS-012 §4) |
| AC-5 | `404` if commodity unknown; `404` if no active registry |
| AC-6 | Response includes `registry_id`, `version`, `effective_from` |

### Definition of Done

- [ ] Contract tests match TDS-010 JSON examples (field names and types)
- [ ] OpenAPI documents endpoints
- [ ] trace_id in logs for each request

### Technical Notes

- Do not expose full internal source credentials in public API
- Cache-Control on registry active: 5 min (TDS-010 §13)
- Reference: [TDS-010](../tds/TDS-010-API-Architecture.md) §10, [TDS-012](../tds/TDS-012-Security-Audit-Architecture.md) §4

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_get_commodities_contract` | httpx contract vs TDS-010 example |
| `test_get_active_registry_contract` | required_agents includes Market, Futures |
| `test_registry_public_anonymous` | No auth header → 200 |

### Traceability

REQ-073, REQ-030 | FD-011, FD-022 | TDS-010 §10

---

## E-02-S06 — Internal Registry Activation API (Ops)

### Summary

Service-key protected endpoint to activate new registry version per TDS-010 §10.3 and TDS-012.

### Dependencies

| Dependency | Type |
|------------|------|
| E-02-S02 | Blocks |
| E-02-S05 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | `POST /v1/internal/registry/versions` creates inactive version (ops payload) |
| AC-2 | `POST /v1/internal/registry/versions/{registry_id}/activate` activates version |
| AC-3 | Requests require `X-API-Key` matching ops service key (TDS-012 §3) |
| AC-4 | Invalid payload returns `400` with validation errors from E-02-S03 |
| AC-5 | Audit log entry for activation with diff hash (prep TDS-012 §6) |

### Definition of Done

- [ ] Rejected without API key in integration test
- [ ] Documented in ops runbook (internal only)

### Technical Notes

- Not exposed to public internet without IP allowlist (TDS-012 §3)
- Two-person approval process is operational policy (TDS-012 §10 PROPOSED)—not automated in this story
- Reference: [TDS-010](../tds/TDS-010-API-Architecture.md) §10.3, [TDS-012](../tds/TDS-012-Security-Audit-Architecture.md)

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_internal_registry_requires_api_key` | 401 without key |
| `test_activate_registry_swaps_active` | Integration |

### Traceability

REQ-073 | TDS-012 §3, §10 | FD-022

---

## E-02-S07 — Registry Service Integration with MI Pipeline Stub

### Summary

Expose `RegistryService.get_active_config(commodity_id)` for downstream epics; verify cotton config consumable by agent orchestration stub.

### Dependencies

| Dependency | Type |
|------------|------|
| E-02-S04 | Blocks |
| E-02-S05 | Blocks |

### Acceptance Criteria

| # | Criterion |
|---|-----------|
| AC-1 | Single entry point used by future E-04 orchestration (import from service module) |
| AC-2 | In-memory cache of active registry with 5-minute TTL (optional, invalidate on activation) |
| AC-3 | Stub test invokes "load registry → list required agents" without starting full pipeline |
| AC-4 | Missing active registry raises typed error `RegistryNotFoundError` |
| AC-5 | Commodity-configurable: only `cotton` returns data Phase 1; others `404` |

### Definition of Done

- [ ] Documented import path for E-03/E-04 teams
- [ ] No duplicate registry read logic outside service

### Technical Notes

- TC-009 commodity-configurable architecture
- Reference: [TDS-003](../tds/TDS-003-Service-Architecture.md) §4.1, [TDS-009](../tds/TDS-009-Market-Intelligence-Framework.md) §12.3

### Test Requirements

| Test | Requirement |
|------|-------------|
| `test_registry_service_cotton` | Returns required Market, Futures |
| `test_registry_cache_invalidation` | After activate, cache refreshes |

### Traceability

REQ-096 | FD-022 | TC-009

---

## Epic E-02 Definition of Done

| Gate | Condition |
|------|-----------|
| M1 registry | All E-02 stories Done |
| Cotton live | Active registry v1.0.0 seeded in dev |
| APIs | Public registry endpoints match TDS-010 contracts |
| E-03 unblocked | Ingestion can read `price_sources` / `arrival_sources` from active registry |

## Epic Dependencies

| Epic | Relationship |
|------|--------------|
| E-00 | Required |
| E-01 | Required (schema + Redis client) |
| E-03 | Blocked until E-02-S04, E-02-S07 |

## Open Questions (Epic Level)

| ID | Item |
|----|------|
| — | Final cotton signal weights founder sign-off (TDS-009 PROPOSED values used in E-02-S04) |
| — | Two-person registry approval automation (TDS-012 PROPOSED) |

## Founder / Architecture Approvals

| Item | Status |
|------|--------|
| Cotton-first | **Approved** (FD-001) |
| MSP ±3%, partial 50% | **Approved** |
| required_agents / optional_agents | **Architecture review** |
| Six participant roles on profile | **Architecture review** |
| phase_1_active_roles Farmer, Trader only | **Baseline** (TDS-009) |
