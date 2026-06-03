# ADR-005: Agent Package Naming — Global Agent Path

| Field | Value |
|-------|-------|
| **Status** | Accepted (implementation standard) |
| **Date** | 2026-06-03 |
| **Deciders** | Engineering (E-00-S02) |
| **Supersedes** | TDS-013 directory label `agents/global/` for **code layout only** |

## Context

TDS-013 §2 lists `agents/global/` for the Global Agent (TDS-004). In Python, `global` is a reserved keyword: `import agents.global` and `from agents.global import ...` are syntax errors. E-00-S01 scaffold used the TDS path; readiness review **C-003** flagged this before E-04 agent wiring.

## Decision

1. Rename the repository package directory from `agents/global/` to **`agents/global_signals/`**.
2. Canonical import path: `agents.global_signals` (valid standard import).
3. **TDS-004 Global Agent** semantics unchanged — only the on-disk package name differs from the TDS-013 diagram label.
4. Update implementation references: layout manifest, tests, and repository scaffold; **do not** alter frozen TDS documents.
5. Registry / event strings (e.g. agent type `GLOBAL`) remain per TDS-004 enums — not tied to the Python package folder name.

## Alternatives Considered

| Option | Rejected because |
|--------|------------------|
| Keep `agents/global/` + `importlib.import_module("agents.global")` only | Fragile; breaks static analysis, IDEs, and import-linter |
| `agents/global_agent/` | Acceptable; team chose `global_signals` to align with signal-domain naming |
| Change TDS-013 in Wave 3 | Architecture frozen — implementation recorded in ADR |

## Consequences

**Positive**
- Valid Python imports and mypy/ruff coverage from E-00-S02 onward.
- Resolves readiness review C-003 without architecture change to agent behavior.

**Negative**
- Minor drift between TDS-013 §2 diagram (`global/`) and repo path (`global_signals/`). Readers should use this ADR as the source of truth for code layout.

## Compliance

| Source | Reference |
|--------|-----------|
| TDS-004 | Global Agent definition |
| TDS-013 | §2 directory diagram (label superseded for code by this ADR) |
| ADR-001 | Monorepo layout and import boundaries |
| Stories | E-00-S01, E-00-S02, E-04 |

## Notes

When TDS-013 is next revised in a formal architecture wave, align §2 to `global_signals/` for consistency. Until then, ADR-005 governs implementation.
