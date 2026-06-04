#!/usr/bin/env python3
"""PI11 Track A: Train and evaluate 30d forecast baselines (sklearn; no LLM).

Usage:
    uv run python scripts/train_forecast_baselines.py --fixture --write-report

    DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \\
        uv run python scripts/train_forecast_baselines.py --write-report
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
from backend.app.services.forecast.baseline_handoff import BaselineHandoffService
from forecasting.datasets.training import (
    load_database_training_dataset,
    load_fixture_training_dataset,
)
from forecasting.models.pipeline import (
    DEFAULT_MODELS_DIR,
    evaluate_all_baselines,
    export_metrics_json,
)
from forecasting.models.report import render_forecast_baseline_report

DEFAULT_REPORT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reviews"
    / "FORECAST_BASELINE_REPORT.md"
)
DEFAULT_METRICS_JSON = (
    Path(__file__).resolve().parents[1] / "data" / "forecast_models" / "baseline_metrics.json"
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
                "tests/unit/test_forecast_baseline_models.py",
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
        description="Train/evaluate 30d forecast baselines (naive, linear, random forest)"
    )
    parser.add_argument(
        "--fixture",
        action="store_true",
        help="Use PI10 deterministic fixtures (no DATABASE_URL)",
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=30,
        help="Forecast horizon in days (default: 30)",
    )
    parser.add_argument(
        "--window-start",
        type=date.fromisoformat,
        default=None,
        help="Inclusive as_of_date lower bound (database mode)",
    )
    parser.add_argument(
        "--window-end",
        type=date.fromisoformat,
        default=None,
        help="Inclusive as_of_date upper bound (database mode)",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=DEFAULT_MODELS_DIR,
        help="Directory for joblib artifacts",
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
    parser.add_argument(
        "--no-save-models",
        action="store_true",
        help="Skip full-corpus joblib export",
    )
    parser.add_argument(
        "--sync-services",
        action="store_true",
        help="Register baselines in ForecastModelRegistry + ForecastQualityService (needs DB)",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    database_url = os.environ.get("DATABASE_URL") or get_settings().database_url

    if args.fixture:
        dataset = load_fixture_training_dataset(horizon_days=args.horizon_days)
    else:
        if not database_url:
            print("DATABASE_URL required (or pass --fixture)", file=sys.stderr)
            return 1
        window_start = args.window_start or DEFAULT_DB_WINDOW_START
        window_end = args.window_end or DEFAULT_DB_WINDOW_END
        engine = create_engine(database_url, pool_pre_ping=True)
        with Session(engine) as session:
            dataset = load_database_training_dataset(
                session,
                horizon_days=args.horizon_days,
                window_start=window_start,
                window_end=window_end,
            )
        engine.dispose()

    results = evaluate_all_baselines(
        dataset,
        output_dir=args.models_dir,
        save_models=not args.no_save_models,
    )
    metrics_path = export_metrics_json(results, DEFAULT_METRICS_JSON)

    for row in results:
        m = row.metrics
        print(
            f"model={row.model_name} mae={m.mae:.4f} rmse={m.rmse:.4f} "
            f"mape_pct={m.mape_pct:.4f} folds={row.fold_count} path={row.model_path}"
        )
    print(f"metrics_json={metrics_path}")

    if args.write_report:
        report = render_forecast_baseline_report(
            dataset,
            results,
            workspace_ref=_git_ref(),
            models_dir=str(args.models_dir),
            metrics_json_path=str(metrics_path),
            pytest_count=_pytest_count(),
        )
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(report, encoding="utf-8")
        print(f"report={args.report_path}")

    if args.sync_services:
        if not database_url:
            print("--sync-services requires DATABASE_URL", file=sys.stderr)
            return 1
        engine = create_engine(database_url, pool_pre_ping=True)
        with Session(engine) as session:
            registered, quality_rows = BaselineHandoffService(session).sync_from_metrics_json(
                metrics_path=metrics_path,
                dataset=dataset,
            )
            session.commit()
        print(
            f"sync_services registry={len(registered)} quality_rows={len(quality_rows)}"
        )
        engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
