"""CLI entry for seed runner (stub until E-02)."""

from __future__ import annotations

import argparse
import sys

from backend.app.persistence.database import SessionLocal
from backend.app.persistence.seeds.runner import SeedRunner


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Apply reference seed fixtures")
    parser.add_argument("fixture", help="Fixture name without .json extension")
    args = parser.parse_args(argv)

    session = SessionLocal()
    try:
        SeedRunner(session).apply(args.fixture)
        session.commit()
    except (FileNotFoundError, NotImplementedError) as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
