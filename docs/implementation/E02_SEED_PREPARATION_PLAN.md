# E-02 Seed Preparation Plan — Cotton v1

**Date:** 2026-06-04  
**Epic:** E-02 Commodity Bootstrap (prep only — no seed execution in E-01 Phase 3)  
**Schema prerequisite:** E-01-S03 (`0002`), E-01-S10 (`0003`)  
**Authoritative weights/agents:** TDS-009 §11.1, ADR-003 only (no new requirements)

---

## 1. Objective

Prepare cotton reference implementation seed data so E-02 can insert **without schema migration**: `commodity`, `commodity_profile`, `commodity_registry` v1.0.0, regions, markets — using `cotton` (not `cotton_test`).

---

## 2. Commodity and Profile (E-02-S01 class)

| Field | Planned value |
|-------|---------------|
| `commodity_id` | `cotton` |
| `status` | `active` |
| `reference_implementation_flag` | `true` |
| `display_name` | Cotton (Shankar / kapas complex) |
| `unit` | quintal |
| `currency` | INR |
| `participant_roles_enabled` | Farmer, Trader, Ginner, Miller, Exporter, Aggregator |
| `phase_1_active_roles` | Farmer, Trader |

---

## 3. CommodityRegistry v1.0.0 (TDS-009 §11.1)

| Field | Value |
|-------|-------|
| `version` | `1.0.0` |
| `is_active` | `true` |
| `effective_from` | Program go-live date (E-02 execution) |
| `required_agents` | `["Market", "Futures"]` |
| `optional_agents` | `["Weather", "Policy", "Demand", "Global"]` |
| `signal_weights` | Futures 0.25, Market 0.22, Policy 0.15, Demand 0.15, Weather 0.13, Global 0.10 |
| `regime_priority` | DATA_DEGRADED, MSP_FLOOR, CURVE_BACKWARDATION, TIGHT_SUPPLY, EXPORT_PUSH, NORMAL |
| `decision_rules` | `msp_proximity_pct` 0.03, `default_partial_sell_pct` 0.50, `formula_version` v1.0.0 |
| `forecast_horizons` | [30, 60, 90] |

**Validation:** `CommodityRegistryRepository.insert_version` + registry validators (E-01-S10); weights must sum to 1.0 over active agents.

---

## 4. Regions and Markets (E-02-S02+)

| Item | Plan |
|------|------|
| Scope | 50–150 mandis (per S04 readiness); prioritize Gujarat, Maharashtra, Telangana cotton belts |
| `region.type` | state → mandi hierarchy |
| `external_refs` | Agmarknet market codes in `source_identifiers` |
| FK | All markets reference seeded regions and `commodity_id=cotton` |

No observation rows in E-02 seed (historical bootstrap is E-03).

---

## 5. Agent Readiness vs Registry

| Agent | Registry class | E-00 / E-03 dependency |
|-------|----------------|------------------------|
| Market | Required | Agmarknet ingest |
| Futures | Required | DS-001 licensed feed |
| Weather | Optional | Weather pipeline |
| Policy | Optional | MSP/CCI sources |
| Demand | Optional | Balance sheets |
| Global | Optional | USDA/ICAC |

MI publish aborts if required agents missing (TDS-009 §9).

---

## 6. Seed Execution Checklist (E-02)

| # | Task | Owner |
|---|------|-------|
| 1 | Idempotent seed script under `backend/app/persistence/seeds/` | E-02 |
| 2 | Insert registry v1.0.0 single active row | E-02 |
| 3 | Verify `RegistryService.get_active_config("cotton")` | E-02 |
| 4 | Document seed rollback (deactivate registry, not DELETE) | E-02 |
| 5 | Integration test uses `cotton_test` id to avoid collision | E-01-S11 |

---

## 7. Blockers

| Blocker | Status |
|---------|--------|
| E-01-S03 + S10 schema | **Green** |
| DS-001 futures | **Yellow** — Futures agent cannot be production-complete until contract |
| E-01-S04 observations | **Green** after Phase 3 — markets can receive rows post-ingest |

---

*End of E-02 seed preparation plan.*
