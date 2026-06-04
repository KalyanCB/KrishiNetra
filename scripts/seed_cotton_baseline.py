#!/usr/bin/env python3
"""Bootstrap cotton commodity + registry v1.0.0 (E-02-S04).

Usage:
    uv run python scripts/seed_cotton_baseline.py
"""

from __future__ import annotations

import sys

from backend.app.persistence.database import SessionLocal
from backend.app.persistence.seeds.runner import SeedRunner


def main() -> int:
    session = SessionLocal()
    try:
        SeedRunner(session).apply("cotton")
        session.commit()
        print("Cotton baseline seed applied (idempotent).")
    except Exception as exc:
        session.rollback()
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
