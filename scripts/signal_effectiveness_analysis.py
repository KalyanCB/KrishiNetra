#!/usr/bin/env python3
"""PI10 Track E: Signal effectiveness vs forward cotton prices.

Statistical correlation only (Pearson + Spearman) — no ML.

Usage:
    DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \\
        uv run python scripts/signal_effectiveness_analysis.py --write-report

    uv run python scripts/signal_effectiveness_analysis.py --fixture-only --write-report
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.services.research.signal_effectiveness.analysis import (
    run_signal_effectiveness_analysis,
)
from backend.app.services.research.signal_effectiveness.data_source import (
    DEFAULT_WINDOW_END,
    DEFAULT_WINDOW_START,
    resolve_data_source,
)
from backend.app.services.research.signal_effectiveness.report import (
    render_signal_effectiveness_report_markdown,
)

DEFAULT_REPORT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reviews"
    / "SIGNAL_EFFECTIVENESS_REPORT.md"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--start-date",
        type=date.fromisoformat,
        default=DEFAULT_WINDOW_START,
        help="Inclusive evaluation window start",
    )
    parser.add_argument(
        "--end-date",
        type=date.fromisoformat,
        default=DEFAULT_WINDOW_END,
        help="Inclusive evaluation window end",
    )
    parser.add_argument(
        "--fixture-only",
        action="store_true",
        help="Skip DATABASE_URL; use synthetic fixture panel",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write {DEFAULT_REPORT.relative_to(Path.cwd())}",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT,
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON summary to stdout")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    session: Session | None = None
    engine = None

    if not args.fixture_only:
        url = os.environ.get("DATABASE_URL")
        if url:
            engine = create_engine(url, pool_pre_ping=True)
            SessionLocal = sessionmaker(bind=engine)
            session = SessionLocal()

    try:
        panel = resolve_data_source(
            session,
            window_start=args.start_date,
            window_end=args.end_date,
        )
        result = run_signal_effectiveness_analysis(panel)

        if args.json or not args.write_report:
            print(json.dumps(result.to_report_detail(), indent=2))

        if args.write_report:
            body = render_signal_effectiveness_report_markdown(result=result)
            args.report_path.parent.mkdir(parents=True, exist_ok=True)
            args.report_path.write_text(body, encoding="utf-8")
            print(f"Wrote {args.report_path}", file=sys.stderr)

        return 0
    finally:
        if session is not None:
            session.close()
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
