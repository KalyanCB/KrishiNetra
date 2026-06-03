# Architecture Decision Records (Implementation)

**Status:** These ADRs **implement** the frozen TDS-000–TDS-014 baseline. They do not supersede or redesign founder or TDS architecture decisions.

## Index

| ADR | Title | Relates to |
|-----|-------|------------|
| [ADR-001](./ADR-001-monorepo-module-boundaries.md) | Monorepo layout and import boundaries | TDS-013, FD-006 |
| [ADR-002](./ADR-002-schema-migrations-alembic.md) | PostgreSQL schema migrations | TDS-006, E-01 |
| [ADR-003](./ADR-003-commodity-registry-versioning.md) | CommodityRegistry versioning and activation | TDS-006, TDS-009, E-02 |
| [ADR-004](./ADR-004-local-development-stack.md) | Local development dependencies | TDS-013, E-00 |
| [ADR-005](./ADR-005-agent-package-naming.md) | Global Agent package path (`global_signals`) | TDS-004, TDS-013, E-00 |

## When to Add a New ADR

Add an ADR only for **implementation choices** not specified in TDS (e.g. Alembic vs raw SQL, `uv` vs `poetry`). Do not use ADRs to change agents, APIs, or domain boundaries defined in TDS.
