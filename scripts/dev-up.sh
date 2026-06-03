#!/usr/bin/env bash
# Start local PostgreSQL 15+ and Redis 7+ (E-00-S06, ADR-004).
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required for local dev stack." >&2
  exit 1
fi

docker compose -f docker-compose.dev.yml up -d
echo "Waiting for health checks..."
docker compose -f docker-compose.dev.yml ps
echo ""
echo "DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5432/krishinetra"
echo "REDIS_URL=redis://127.0.0.1:6379/0"
echo "Copy .env.example to .env if needed, then: ./scripts/verify-dev-connect.sh"
