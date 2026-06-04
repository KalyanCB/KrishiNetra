#!/usr/bin/env python3
"""PI5 Track C: persist Agmarknet fixture observations and emit proof JSON.

Usage:
    DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \\
        uv run python scripts/observation_population_proof.py
"""

from __future__ import annotations

import json
import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.spike.agmarknet.population import (
    ObservationCounts,
    run_population_proof,
)


def _counts_dict(counts: ObservationCounts) -> dict[str, int]:
    return {"price": counts.price, "arrival": counts.arrival, "total": counts.total}


def main() -> int:
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL required", file=sys.stderr)
        return 1

    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            result = run_population_proof(session)
    except Exception as exc:
        print(f"Population proof failed: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    payload = {
        "verdict": "PASS" if result.fk_valid and result.inserted.total > 0 else "FAIL",
        "fixture_path": result.fixture_path,
        "ogd_record_count": result.ogd_record_count,
        "draft_price_count": result.draft_price_count,
        "draft_arrival_count": result.draft_arrival_count,
        "before": _counts_dict(result.before),
        "after": _counts_dict(result.after),
        "inserted": _counts_dict(result.inserted),
        "fk_valid": result.fk_valid,
        "sample_prices": result.sample_prices,
        "sample_arrivals": result.sample_arrivals,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0 if payload["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
