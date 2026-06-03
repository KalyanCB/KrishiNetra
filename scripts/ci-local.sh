#!/usr/bin/env bash
# Mirror .github/workflows/ci.yml locally (E-00-S04).
set -euo pipefail

cd "$(dirname "$0")/.."

uv sync --extra dev
uv run python tests/unit/test_repo_layout.py
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_imports.py
uv run mypy

if [[ -n "${DATABASE_URL:-}" ]]; then
  uv run alembic upgrade head
fi

uv run pytest
