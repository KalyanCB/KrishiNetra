#!/usr/bin/env python3
"""Manual Agmarknet OGD ingest (E-03-S01). No scheduler — run on demand.

Usage (fixture, no API key):
    DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5432/krishinetra \\
        uv run python scripts/agmarknet_ingest.py --fixture

Usage (live OGD API):
    DATABASE_URL=... OGD_API_KEY=... uv run python scripts/agmarknet_ingest.py \\
        --state Telangana --commodity Cotton --arrival-date 26/03/2022
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.config.settings import get_settings
from backend.app.persistence.seeds.runner import SeedRunner
from backend.app.services.ingest.agmarknet.pipeline import (
    AgmarknetIngestPipeline,
    build_ogd_client,
)

DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "agmarknet"
    / "ogd_telangana_sample.json"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agmarknet OGD ingest (manual)")
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Ingest tests/fixtures/agmarknet/ogd_telangana_sample.json",
    )
    parser.add_argument("--fixture-path", type=Path, default=None)
    parser.add_argument("--state", type=str, default=None, help="OGD filters[state]")
    parser.add_argument(
        "--district", type=str, default=None, help="OGD filters[district]"
    )
    parser.add_argument(
        "--commodity", type=str, default=None, help="OGD filters[commodity]"
    )
    parser.add_argument(
        "--arrival-date",
        type=str,
        default=None,
        help="OGD filters[arrival_date] (DD/MM/YYYY)",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip cotton baseline seed before ingest",
    )
    return parser.parse_args()


def _build_filters(args: argparse.Namespace) -> dict[str, str]:
    filters: dict[str, str] = {}
    if args.state:
        filters["state"] = args.state
    if args.district:
        filters["district"] = args.district
    if args.commodity:
        filters["commodity"] = args.commodity
    if args.arrival_date:
        filters["arrival_date"] = args.arrival_date
    return filters


def main() -> int:
    args = _parse_args()
    db_url = os.environ.get("DATABASE_URL") or get_settings().database_url
    if not db_url:
        print("DATABASE_URL required", file=sys.stderr)
        return 1

    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            if not args.no_seed:
                SeedRunner(session).apply("cotton")
                session.flush()

            if args.fixture:
                path = args.fixture_path or DEFAULT_FIXTURE
                pipeline = AgmarknetIngestPipeline(session)
                result = pipeline.ingest_from_fixture(path)
            else:
                api_key = get_settings().ogd_api_key
                if not api_key:
                    print(
                        "OGD_API_KEY required for live ingest (or use --fixture)",
                        file=sys.stderr,
                    )
                    return 1
                client = build_ogd_client(api_key)
                pipeline = AgmarknetIngestPipeline(session, ogd_client=client)
                result = pipeline.ingest_from_ogd(filters=_build_filters(args))

            session.commit()
    except Exception as exc:
        print(f"Agmarknet ingest failed: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    payload = {
        "ogd_rows_fetched": result.ogd_rows_fetched,
        "ogd_rows_parsed": result.ogd_rows_parsed,
        "price_drafts": result.price_drafts,
        "arrival_drafts": result.arrival_drafts,
        "prices_inserted": result.prices_inserted,
        "arrivals_inserted": result.arrivals_inserted,
        "prices_skipped_duplicate": result.prices_skipped_duplicate,
        "arrivals_skipped_duplicate": result.arrivals_skipped_duplicate,
        "total_inserted": result.total_inserted,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
