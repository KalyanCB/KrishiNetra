# E-00 — Declared Dependencies Not Yet Used in Application Code

**Epic:** E-00 Program Foundation (M0)  
**Date:** 2026-06-03  
**Related:** [E-00-S02](../stories/E-00-Program-Foundation.md), [ADR-004](../adrs/ADR-004-local-development-stack.md), [ADR-002](../adrs/ADR-002-schema-migrations-alembic.md)

M0 pins core libraries in root `pyproject.toml` for reproducible installs and CI. Several packages are **declared but not imported** by production modules yet. This is intentional: epics below own first use.

---

## Summary

| Package | Declared in E-00 | First use (planned) | M0 usage today |
|---------|------------------|---------------------|----------------|
| **SQLAlchemy** | E-00-S02 AC-4 | **E-01** — repositories, canonical schema (TDS-006) | Integration test only (`tests/integration/test_db_redis_connect.py`) when compose is up |
| **Redis** | E-00-S02 AC-4 | **E-01** — MI snapshot cache keys (TDS-006 §4, TDS-009 §8) | Same integration test; `docker-compose.dev.yml` Redis 7+ |
| **Alembic** | E-00-S02 AC-4 | **E-01** — versioned migrations ([ADR-002](../adrs/ADR-002-schema-migrations-alembic.md)) | Not invoked; no `alembic/` env in repo until E-01-S01 |
| **LangGraph** | E-00-S02 technical note | **E-04** — agent orchestration (TDS-004); not decision_engine | Not imported anywhere (ADR-001: no LLM in deterministic paths at M0) |

---

## Rationale by package

### SQLAlchemy

- **Why declared at M0:** ADR-004 and TDS-013 assume PostgreSQL 15+ as the canonical store; E-01-S02+ need a single ORM stack from day one of schema work.
- **Why not in `backend/app` yet:** E-00-S03 is a health-only shell; no persistence layer until E-01.
- **M0 proof:** `scripts/verify-dev-connect.sh` and optional integration test validate `DATABASE_URL` against local compose.

### Redis

- **Why declared at M0:** Local dev stack (E-00-S06) and future MI hot-path reads require a pinned client.
- **Why not in `backend/app` yet:** No cache keys or snapshot materialization until E-01/E-09.
- **M0 proof:** Compose service + integration ping when `REDIS_URL` is set.

### Alembic

- **Why declared at M0:** E-01-S01 acceptance criteria require Alembic bootstrap and reversible migrations (ADR-002); locking the tool avoids a mid-epic dependency churn.
- **Why not run yet:** No DDL in E-00; migrations are explicitly out of scope per E-00-S06 technical notes.

### LangGraph

- **Why declared at M0:** E-00-S02 technical note allows early pin for reproducibility; orchestration belongs to agent epics, not the FastAPI shell.
- **Why not imported:** Import boundaries (E-00-S05) forbid LLM SDKs in `decision_engine`; domain agents are stubs; LangGraph wiring is **E-04** only under `agents/orchestration/` per TDS-004.

---

## Packages used at M0 (contrast)

| Package | M0 role |
|---------|---------|
| FastAPI / Uvicorn | API shell, `/health`, `/v1` stubs |
| Pydantic / pydantic-settings | `StructuredSignal`, settings prep |
| httpx | API smoke tests |
| psycopg2-binary | Postgres connectivity smoke (E-00-S06) |

---

## References

- [backend/README.md](../../backend/README.md) — setup and local stack
- [E00_COMPLETION_REPORT.md](../reviews/E00_COMPLETION_REPORT.md) — M0 gate evidence
