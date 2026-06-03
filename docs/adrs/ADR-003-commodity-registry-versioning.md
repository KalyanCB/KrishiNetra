# ADR-003: CommodityRegistry Versioning and Agent Requirements

| Field | Value |
|-------|-------|
| **Status** | Accepted (implements TDS-009 extension) |
| **Date** | 2026-06-03 |
| **Deciders** | Lead Architect |
| **Supersedes** | TDS-006 `minimum_agents[]` as sole gate (implementation uses split lists) |

## Context

Architecture review (Wave 3) requires:

- `required_agents[]` — pipeline aborts MI publish if missing
- `optional_agents[]` — missing applies confidence penalty (TDS-009)
- `signal_weights` per commodity
- Versioned activation without retroactive mutation (FD-022, TDS-012 §10)

TDS-006 §3.3 referenced `minimum_agents[]`; TDS-009 §4.1 defines required/optional split. Implementation follows **TDS-009** as the operational contract.

## Decision

1. `commodity_registry` table stores:
   - `required_agents` (JSON array of AgentType strings)
   - `optional_agents` (JSON array)
   - `signal_weights` (JSON object agent → float)
   - `regime_priority` (JSON array)
   - `decision_rules` (JSON: msp_proximity_pct, default_partial_sell_pct, formula_version)
2. Exactly one `is_active=true` row per `commodity_id` (partial unique index).
3. Activation swaps active flag in a transaction; prior version gets `effective_to`.
4. Cotton v1.0.0 seed values from TDS-009 §11.1 (E-02-S04).
5. Downstream pipelines read config only via `RegistryService.get_active_config()`.

## Consequences

**Positive**
- Clear publish gate for MI (TDS-009 §9).
- Supports commodity-configurable expansion (FD-022, Phase 7).

**Negative**
- Validator must run on every new version (E-02-S03).

## Compliance

| Source | Reference |
|--------|-----------|
| TDS-009 | §4.1, §11.1, §12 |
| TDS-010 | §10 Registry APIs |
| TDS-012 | §10 Registry governance |
| FD-001, FD-008, FD-022 | Cotton, MSP rule, configurable |
| REQ-073, REQ-074 | Registry |
| Stories | E-01-S10, E-02-S02–S07 |

## Founder Clarifications Embedded

| Rule | Value |
|------|-------|
| msp_proximity_pct | 0.03 |
| default_partial_sell_pct | 0.50 |
| Cotton required agents | Market, Futures |

## Notes

Does not introduce new product requirements—implements frozen TDS-009 cotton reference and architecture review fields.
