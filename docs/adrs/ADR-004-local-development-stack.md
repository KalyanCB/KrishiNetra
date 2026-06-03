# ADR-004: Local Development Stack

| Field | Value |
|-------|-------|
| **Status** | Accepted (implementation standard) |
| **Date** | 2026-06-03 |
| **Deciders** | Engineering (Sprint 0) |
| **Supersedes** | None |

## Context

E-00 requires local PostgreSQL and Redis (TDS-013 F-00-03). Production infrastructure (Terraform, Docker prod) is explicitly Wave 4+ out of scope for current stories.

## Decision

1. **Local dependencies** via `docker-compose.dev.yml` (or equivalent) providing:
   - PostgreSQL 15+
   - Redis 7+
2. **Environment template** `.env.example` with `DATABASE_URL`, `REDIS_URL`, `LOG_LEVEL`.
3. **Package manager:** **`uv`** (locked E-00-S02). Lockfile: `uv.lock` at repo root. Setup: `uv sync --extra dev` — see `backend/README.md`.
4. **No LLM API keys** required for E-00–E-02 stories.

## Alternatives Considered

| Option | Rejected because |
|--------|------------------|
| Embedded SQLite | Approved stack is PostgreSQL; partitioning/replay needs Postgres |
| Shared cloud dev DB only | Slow onboarding; violates <15 min setup goal |

## Consequences

**Positive**
- Matches approved PostgreSQL + Redis architecture.
- Enables E-01 integration tests on CI with service containers.

**Negative**
- Developers need Docker installed.

## Compliance

| Source | Reference |
|--------|-----------|
| TDS-013 | §1, F-00-03 |
| Stories | E-00-S06, E-01-S01 |

## Notes

**Locked (E-00-S02):** `uv` with root `pyproject.toml` and `uv.lock`.
