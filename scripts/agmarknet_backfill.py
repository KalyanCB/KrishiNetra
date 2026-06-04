#!/usr/bin/env python3
"""PI7 Track A: Historical Agmarknet cotton backfill for cotton belt mandis.

Usage (fixture replay, no API key):
    DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5432/krishinetra \\
        uv run python scripts/agmarknet_backfill.py --fixture --dry-run

Usage (live OGD, 36-month window):
    DATABASE_URL=... OGD_API_KEY=... uv run python scripts/agmarknet_backfill.py \\
        --start-date 2023-06-01 --end-date 2026-06-03

Stats only (no ingest):
    uv run python scripts/agmarknet_backfill.py --stats \\
        --start-date 2023-06-01 --end-date 2026-06-03 --write-report
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.config.settings import get_settings
from backend.app.services.ingest.agmarknet.backfill import (
    DEFAULT_BACKFILL_MONTHS,
    AgmarknetBackfillPipeline,
    BackfillWindow,
    FixtureReplayOgdClient,
    build_backfill_ogd_client,
    compute_backfill_stats,
    default_backfill_window,
    render_backfill_report_markdown,
)
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_expected_market_ids,
    load_telangana_primary_market_ids,
)

DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "agmarknet"
    / "ogd_telangana_sample.json"
)
DEFAULT_REPORT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reviews"
    / "HISTORICAL_BACKFILL_REPORT.md"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=None,
        help="Inclusive window start (ISO date)",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=None,
        help="Inclusive window end (ISO date)",
    )
    parser.add_argument(
        "--months",
        type=int,
        default=DEFAULT_BACKFILL_MONTHS,
        help=f"Calendar months when start/end omitted (default: {DEFAULT_BACKFILL_MONTHS})",
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Replay tests/fixtures/agmarknet/ogd_telangana_sample.json per day",
    )
    parser.add_argument("--fixture-path", type=Path, default=None)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and map; roll back each day (no persist)",
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Compute DB coverage only (skip ingest unless not set with ingest flags)",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write docs/reviews/HISTORICAL_BACKFILL_REPORT.md from stats",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT,
        help="Markdown report output path",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Skip cotton baseline seed before backfill",
    )
    parser.add_argument(
        "--scope",
        choices=("telangana", "belt"),
        default="belt",
        help="Coverage stats scope: full cotton belt seed (default) or 4 TG mandis",
    )
    return parser.parse_args()


def _resolve_expected_market_ids(scope: str) -> tuple[str, ...]:
    if scope == "belt":
        return load_expected_market_ids()
    return load_telangana_primary_market_ids()


def _resolve_window(args: argparse.Namespace) -> BackfillWindow:
    if args.start_date and args.end_date:
        return BackfillWindow(start=args.start_date, end=args.end_date)
    if args.start_date or args.end_date:
        print("Provide both --start-date and --end-date, or neither", file=sys.stderr)
        raise SystemExit(1)
    default = default_backfill_window(months=args.months)
    return BackfillWindow(start=default.start, end=default.end)


def main() -> int:
    args = _parse_args()
    window = _resolve_window(args)
    db_url = os.environ.get("DATABASE_URL") or get_settings().database_url
    if not db_url:
        print("DATABASE_URL required", file=sys.stderr)
        return 1

    engine = create_engine(db_url, pool_pre_ping=True)
    expected_markets = _resolve_expected_market_ids(args.scope)
    backfill_result = None
    try:
        with Session(engine) as session:
            if not args.stats:
                if args.fixture:
                    path = args.fixture_path or DEFAULT_FIXTURE
                    client: FixtureReplayOgdClient | object = FixtureReplayOgdClient(
                        path
                    )
                else:
                    api_key = get_settings().ogd_api_key
                    if not api_key:
                        print(
                            "OGD_API_KEY required for live backfill (or use --fixture)",
                            file=sys.stderr,
                        )
                        return 1
                    client = build_backfill_ogd_client(api_key)

                pipeline = AgmarknetBackfillPipeline(
                    session,
                    ogd_client=client,  # type: ignore[arg-type]
                    seed_cotton=not args.no_seed,
                    expected_market_ids=expected_markets,
                )
                backfill_result = pipeline.run(window, dry_run=args.dry_run)

            stats = compute_backfill_stats(
                session, window, expected_market_ids=expected_markets
            )

            from backend.app.services.quality.snapshot_service import (
                DataQualitySnapshotService,
            )

            snapshot = DataQualitySnapshotService(
                session
            ).record_after_agmarknet_backfill(
                window_start=window.start,
                window_end=window.end,
                expected_market_ids=expected_markets,
            )
            session.commit()

            if args.write_report:
                report = render_backfill_report_markdown(
                    result=backfill_result,
                    stats=stats,
                    fixture_mode=args.fixture,
                )
                args.report_path.parent.mkdir(parents=True, exist_ok=True)
                args.report_path.write_text(report, encoding="utf-8")
    except Exception as exc:
        print(f"Agmarknet backfill failed: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    payload: dict[str, object] = {
        "window": {
            "start": window.start.isoformat(),
            "end": window.end.isoformat(),
            "days": window.days,
        },
        "dry_run": args.dry_run,
        "fixture_mode": args.fixture,
        "stats": stats.to_dict(),
    }
    payload["quality_snapshot"] = {
        "as_of_date": snapshot.as_of_date.isoformat(),
        "overall_quality_score": str(snapshot.overall_quality_score),
        "agmarknet_lag_hours": (
            str(snapshot.agmarknet_lag_hours)
            if snapshot.agmarknet_lag_hours is not None
            else None
        ),
    }
    if backfill_result is not None:
        payload["ingest"] = {
            "days_fetched": backfill_result.days_fetched,
            "ogd_rows_fetched": backfill_result.ogd_rows_fetched,
            "rows_loaded": backfill_result.rows_loaded,
            "prices_inserted": backfill_result.prices_inserted,
            "arrivals_inserted": backfill_result.arrivals_inserted,
            "markets_expected": len(stats.expected_market_ids),
        }
    if args.write_report:
        payload["report_path"] = str(args.report_path)

    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
