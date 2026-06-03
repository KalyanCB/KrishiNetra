# ADR-001: Monorepo Layout and Import Boundaries

| Field | Value |
|-------|-------|
| **Status** | Accepted (implements frozen architecture) |
| **Date** | 2026-06-03 |
| **Deciders** | Lead Architect |
| **Supersedes** | None |

## Context

TDS-013 defines a modular monolith with strict deterministic/LLM separation (FD-006, TC-001). Implementation must enforce module boundaries in CI to prevent architectural drift.

## Decision

1. Use a **single monorepo** with directories exactly as TDS-013 §2.
2. Enforce import boundaries via CI (E-00-S05) matching TDS-013 §3.1:
   - `decision_engine` must not import LLM SDKs
   - `forecasting` must not import `decision_engine`
   - Domain `agents` must not import `agents.explainability`
   - `shared` must not import upward packages
3. LLM SDK dependencies allowed only under `agents/explainability/`.

## Consequences

**Positive**
- Aligns with frozen TDS; supports REQ-015 and REQ-103 replay integrity.

**Negative**
- Requires discipline when adding utilities; may need shared extraction to `shared/`.

## Compliance

| Source | Reference |
|--------|-----------|
| TDS-013 | §2, §3.1, §7 |
| FD-006 | Agents orchestrate; numbers decide |
| Stories | E-00-S01, E-00-S05 |

## Notes

This ADR does not change architecture—it records **how** the frozen architecture is enforced in code.
