#!/usr/bin/env python3
"""PI6 Track D: NASA POWER weather backfill into weather_observation.

Usage:
    DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \\
        uv run python scripts/nasa_power_ingest.py

    uv run python scripts/nasa_power_ingest.py --months 12 --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from backend.app.persistence.models.weather import (
    WeatherObservationModel,
    WeatherObservationSource,
)
from backend.app.services.ingest.weather.constants import DEFAULT_BACKFILL_MONTHS
from backend.app.services.ingest.weather.pipeline import (
    NasaPowerIngestPipeline,
    default_ingest_end_date,
    ingest_window_start,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--months",
        type=int,
        default=DEFAULT_BACKFILL_MONTHS,
        help=f"Backfill window in calendar months (default: {DEFAULT_BACKFILL_MONTHS})",
    )
    parser.add_argument(
        "--end",
        type=date.fromisoformat,
        default=None,
        help="Inclusive end date (default: today minus NASA POWER lag)",
    )
    parser.add_argument(
        "--start",
        type=date.fromisoformat,
        default=None,
        help="Inclusive start date (overrides --months when set)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and map only; roll back inserts",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip cotton seed apply (regions must already exist)",
    )
    return parser.parse_args()


def _count_nasa_power_rows(session: Session) -> int:
    stmt = (
        select(func.count())
        .select_from(WeatherObservationModel)
        .where(
            WeatherObservationModel.source == WeatherObservationSource.NASA_POWER.value
        )
    )
    return int(session.scalar(stmt) or 0)


def main() -> int:
    args = _parse_args()
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL required", file=sys.stderr)
        return 1

    end = args.end or default_ingest_end_date()
    start = args.start or ingest_window_start(end, months=args.months)
    if start > end:
        print(f"Invalid window: start {start} after end {end}", file=sys.stderr)
        return 1

    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            before = _count_nasa_power_rows(session)
            pipeline = NasaPowerIngestPipeline(
                session,
                seed_cotton=not args.no_seed,
            )
            result = pipeline.ingest_range(start, end, commit=not args.dry_run)
            if args.dry_run:
                session.rollback()
            after = _count_nasa_power_rows(session)
    except Exception as exc:
        print(f"NASA POWER ingest failed: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    payload = {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "months": args.months,
        "dry_run": args.dry_run,
        "points_fetched": result.points_fetched,
        "rows_persisted": result.rows_persisted,
        "rows_skipped_duplicate": result.rows_skipped_duplicate,
        "nasa_power_rows_before": before,
        "nasa_power_rows_after": after,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
