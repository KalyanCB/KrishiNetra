#!/usr/bin/env python3
"""PI10 Track D: Build 30/60/90-day forecast target datasets (export + validation only).

Usage:
    uv run python scripts/build_forecast_datasets.py --fixture --write-report

    DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \\
        uv run python scripts/build_forecast_datasets.py --write-report
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.config.settings import get_settings
from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID
from forecasting.datasets.builder import (
    ForecastDatasetBuilder as Builder,
)
from forecasting.datasets.builder import (
    build_fixture_datasets,
    export_datasets_jsonl,
    render_forecast_dataset_report,
)
from forecasting.datasets.fixtures import (
    FIXTURE_WINDOW_END,
    FIXTURE_WINDOW_START,
    fixture_price_window,
    fixture_primary_markets,
    fixture_snapshots_by_date,
)

DEFAULT_REPORT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reviews"
    / "FORECAST_DATASET_REPORT.md"
)
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data" / "forecast_datasets"
DEFAULT_DB_WINDOW_START = date(2023, 6, 1)
DEFAULT_DB_WINDOW_END = date(2026, 6, 3)


def _git_ref() -> str:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        return proc.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def _pytest_count() -> int | None:
    try:
        proc = subprocess.run(
            [
                "uv",
                "run",
                "pytest",
                "tests/unit/test_forecast_dataset_builder.py",
                "-q",
                "--collect-only",
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        for line in proc.stdout.splitlines():
            if "test" in line and "selected" in line:
                parts = line.split()
                if parts and parts[0].isdigit():
                    return int(parts[0])
        return None
    except (OSError, subprocess.CalledProcessError):
        return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build forecast target datasets for horizons 30/60/90 days"
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use deterministic in-repo fixtures (no DATABASE_URL required)",
    )
    parser.add_argument(
        "--commodity-id",
        default=COTTON_COMMODITY_ID,
        help="Commodity scope (default: cotton)",
    )
    parser.add_argument(
        "--window-start",
        type=date.fromisoformat,
        default=None,
        help="Inclusive as_of_date lower bound (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--window-end",
        type=date.fromisoformat,
        default=None,
        help="Inclusive as_of_date upper bound (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Directory for JSONL exports",
    )
    parser.add_argument(
        "--filename-prefix",
        default="",
        help="Prefix for JSONL filenames (e.g. real_ → real_forecast_target_30d.jsonl)",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write markdown report to {DEFAULT_REPORT}",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT,
        help="Override report output path",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    database_url = os.environ.get("DATABASE_URL") or get_settings().database_url

    if args.fixture:
        result = build_fixture_datasets(
            prices=fixture_price_window(),
            snapshots_by_date=fixture_snapshots_by_date(),
            commodity_id=args.commodity_id,
            window_start=args.window_start or FIXTURE_WINDOW_START,
            window_end=args.window_end or FIXTURE_WINDOW_END,
            primary_market_ids=fixture_primary_markets(),
        )
        db_url_for_report: str | None = None
    else:
        if not database_url:
            print("DATABASE_URL required (or pass --fixture)", file=sys.stderr)
            return 1
        window_start = args.window_start or DEFAULT_DB_WINDOW_START
        window_end = args.window_end or DEFAULT_DB_WINDOW_END
        engine = create_engine(database_url, pool_pre_ping=True)
        with Session(engine) as session:
            result = Builder(session).build_from_database(
                commodity_id=args.commodity_id,
                window_start=window_start,
                window_end=window_end,
            )
        engine.dispose()
        db_url_for_report = database_url

    paths = export_datasets_jsonl(
        result, args.output_dir, filename_prefix=args.filename_prefix
    )
    for horizon, path in sorted(paths.items()):
        stat = result.stats[horizon]
        print(f"horizon_{horizon}d rows={stat.row_count} path={path}")

    if args.write_report:
        report = render_forecast_dataset_report(
            result,
            workspace_ref=_git_ref(),
            database_url=db_url_for_report,
            output_dir=str(args.output_dir),
            pytest_count=_pytest_count(),
        )
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(report, encoding="utf-8")
        print(f"report={args.report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
