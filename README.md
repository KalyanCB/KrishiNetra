# KrishiNetra

Decision intelligence platform for agricultural inventory decisions (cotton-first, Phase 1).

## Documentation

| Package | Path |
|---------|------|
| Founder intent | [docs/founder/](docs/founder/) |
| Technical design (TDS) | [docs/tds/](docs/tds/) |
| Implementation stories | [docs/stories/](docs/stories/) |
| Architecture decision records | [docs/adrs/](docs/adrs/) |
| Reviews | [docs/reviews/](docs/reviews/) |

## Repository layout

See [TDS-013 Repository Architecture](docs/tds/TDS-013-Repository-Architecture.md) for the modular monolith structure.

## Developer setup

```bash
uv sync --extra dev
uv run pytest tests/unit/ -v
```

See [backend/README.md](backend/README.md) for workspace details.

## Status

**Release:** `0.1.0-dev` — E-00 M0 (program foundation) complete.

| Story | Scope |
|-------|--------|
| E-00-S01–S04 | Scaffold, workspace, API shell, CI (founder-approved) |
| E-00-S05–S08 | Import boundaries, local compose, trace_id logging, shared enums |

Completion evidence: [docs/reviews/E00_COMPLETION_REPORT.md](docs/reviews/E00_COMPLETION_REPORT.md).  
Dependency rationale (LangGraph, SQLAlchemy, Redis, Alembic): [docs/implementation/E00_DEPENDENCY_RATIONALE.md](docs/implementation/E00_DEPENDENCY_RATIONALE.md).
