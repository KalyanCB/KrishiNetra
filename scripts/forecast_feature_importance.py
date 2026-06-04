#!/usr/bin/env python3
"""PI11 Track C: Random Forest baseline feature importance by lineage group.

Usage:
    uv run python scripts/forecast_feature_importance.py --fixture --write-report

    DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \\
        uv run python scripts/forecast_feature_importance.py --write-report
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.config.settings import get_settings
from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID
from forecasting.datasets.builder import FORECAST_HORIZONS
from forecasting.datasets.fixtures import FIXTURE_WINDOW_END, FIXTURE_WINDOW_START
from forecasting.features.importance import (
    build_database_panel,
    build_fixture_panel,
    run_feature_importance_analysis,
)
from forecasting.features.report import render_feature_importance_report

DEFAULT_REPORT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reviews"
    / "FEATURE_IMPORTANCE_REPORT.md"
)
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
                "tests/unit/test_forecast_feature_importance.py",
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use deterministic in-repo fixtures (no DATABASE_URL required)",
    )
    parser.add_argument(
        "--horizon",
        type=int,
        default=30,
        choices=FORECAST_HORIZONS,
        help="Target horizon in days (default: 30)",
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
        "--top-k",
        type=int,
        default=10,
        help="Top features retained per lineage group in report",
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
    parser.add_argument("--json", action="store_true", help="Emit JSON summary to stdout")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    database_url = os.environ.get("DATABASE_URL") or get_settings().database_url

    if args.fixture:
        panel = build_fixture_panel(
            horizon_days=args.horizon,
            window_start=args.window_start or FIXTURE_WINDOW_START,
            window_end=args.window_end or FIXTURE_WINDOW_END,
        )
        mode = "fixture"
        window_start = args.window_start or FIXTURE_WINDOW_START
        window_end = args.window_end or FIXTURE_WINDOW_END
    else:
        if not database_url:
            print("DATABASE_URL required (or pass --fixture)", file=sys.stderr)
            return 1
        window_start = args.window_start or DEFAULT_DB_WINDOW_START
        window_end = args.window_end or DEFAULT_DB_WINDOW_END
        engine = create_engine(database_url, pool_pre_ping=True)
        with Session(engine) as session:
            panel = build_database_panel(
                session,
                commodity_id=args.commodity_id,
                window_start=window_start,
                window_end=window_end,
                horizon_days=args.horizon,
            )
        engine.dispose()
        mode = "database"

    result = run_feature_importance_analysis(
        panel,
        horizon_days=args.horizon,
        mode=mode,
        commodity_id=args.commodity_id,
        top_k=args.top_k,
    )

    if args.json or not args.write_report:
        print(json.dumps(result.to_report_detail(), indent=2))

    if args.write_report:
        report = render_feature_importance_report(
            result,
            workspace_ref=_git_ref(),
            pytest_count=_pytest_count(),
        )
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(report, encoding="utf-8")
        print(f"report={args.report_path}", file=sys.stderr)

    for prefix in ("market", "weather", "futures"):
        tops = result.top_per_group.get(prefix, ())
        if tops:
            top_name, top_score = tops[0]
            print(f"{prefix}_top={top_name} importance={top_score:.6f}")
        else:
            print(f"{prefix}_top=(none)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
