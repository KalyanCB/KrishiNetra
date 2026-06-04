# Backend — KrishiNetra

FastAPI application shell (`backend.app`). Entrypoint: `backend.app.main:app` (E-00-S03).

## Prerequisites

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/) (package manager — locked in [ADR-004](../docs/adrs/ADR-004-local-development-stack.md))

## One-command setup

From the **repository root**:

```bash
uv sync --extra dev
```

Editable install exposes monorepo packages (`shared`, `agents`, `forecasting`, `decision_engine`, `market_intelligence`, `backend`) for imports and tests.

Alternative (pip):

```bash
python3 -m pip install -e ".[dev]"
```

## Run API locally

```bash
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: `GET http://127.0.0.1:8000/health` → `{"status":"ok"}`
- OpenAPI: `http://127.0.0.1:8000/docs`
- v1 stubs mounted at `/v1` (501 until E-09)

## Verify workspace (same as CI)

```bash
./scripts/ci-local.sh
```

Or step by step:

```bash
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

## Tooling (E-00-S02)

| Tool | Config | Purpose |
|------|--------|---------|
| uv | `uv.lock` | Lockfile and sync |
| Ruff | `pyproject.toml` `[tool.ruff]` | Lint and format (TDS-013 §5.1) |
| Black | `pyproject.toml` `[tool.black]` | Optional formatter |
| MyPy | `pyproject.toml` `[tool.mypy]` | Type checking |
| pytest | `pyproject.toml` `[tool.pytest.ini_options]` | Unit tests |

## Local development stack (E-00-S06)

From the **repository root** (macOS or Linux; Docker required):

```bash
cp .env.example .env
./scripts/dev-up.sh
./scripts/verify-dev-connect.sh
uv sync --extra dev
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- `docker-compose.dev.yml` — PostgreSQL 15+ and Redis 7+ (dev only; not production IaC)
- Health endpoint works without DB/Redis; use `verify-dev-connect.sh` after compose is up
- Integration test: `DATABASE_URL` and `REDIS_URL` set → `uv run pytest tests/integration/ -v`

Target: clone → health endpoint in under 15 minutes on a clean machine with Docker + uv.

## Database migrations (E-01-S01+)

Requires local PostgreSQL (`./scripts/dev-up.sh`) and `DATABASE_URL` in `.env`:

```bash
uv run alembic upgrade head
uv run alembic current
```

See [backend/app/persistence/README.md](app/persistence/README.md) for naming convention and rollback commands.

## Out of scope (E-00-S03 shell)

- Business logic in handlers (E-09+)
- LLM SDK packages (ADR-001 — only under `agents/explainability/` in later stories)

## Redis MI cache (E-01-S09)

Redis holds a **cache-only** denormalized MI snapshot projection per TDS-006 §4 and TDS-009 §8. PostgreSQL remains the source of truth.

| Item | Value |
|------|-------|
| Key pattern | `mi:{commodity_id}:{as_of_date}` |
| Default TTL | 48 hours (`MI_CACHE_TTL_SECONDS`, default `172800`) |
| Env | `REDIS_URL` (see `.env.example`) |
| Client | `backend.app.cache.mi_projection.RedisMIProjectionClient` |
| Payload contract | `shared.contracts.mi_snapshot.MISnapshotPayload` |

```python
from datetime import date
from backend.app.cache import build_mi_cache_key, get_mi_projection_client

client = get_mi_projection_client()
key = build_mi_cache_key("cotton", date(2026, 6, 4))
client.set_mi_snapshot(key, payload_dict)  # JSON-serialized
cached = client.get_mi_snapshot(key)  # None on miss or Redis down
```

Materialization from PostgreSQL: `backend.app.services.mi_snapshot_materializer.MISnapshotMaterializer`.

Unit tests: `tests/unit/test_redis_mi.py` (`test_redis_mi_roundtrip`, `test_redis_key_format`).

## Declared dependencies (not yet used in app code)

SQLAlchemy, Redis, Alembic, and LangGraph are pinned in root `pyproject.toml` for reproducible installs. **Redis is wired** for MI cache (E-01-S09); remaining packages follow epic ownership: [E00_DEPENDENCY_RATIONALE.md](../docs/implementation/E00_DEPENDENCY_RATIONALE.md).

## Agent package naming

The Global Agent package path is `agents/global_signals/` per [ADR-005](../docs/adrs/ADR-005-agent-package-naming.md) (not `agents/global/`, which is invalid in Python).
