#!/usr/bin/env python3
"""PI11 Track A / PI12 Track C: Train and evaluate forecast baselines (sklearn; no LLM).

Usage:
    uv run python scripts/train_forecast_baselines.py --fixture --write-report

    uv run python scripts/train_forecast_baselines.py --real --write-report

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
from uuid import UUID

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.config.settings import get_settings
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.services.forecast.baseline_handoff import (
    COTTON_COMMODITY_ID,
    BaselineHandoffService,
)
from backend.app.services.registry.service import RegistryNotFoundError, RegistryService
from forecasting.datasets.training import (
    load_database_training_dataset,
    load_fixture_training_dataset,
    load_real_training_dataset,
    real_forecast_jsonl_path,
)
from forecasting.models.pipeline import (
    DEFAULT_MODELS_DIR,
    best_non_naive_beats_naive,
    evaluate_all_baselines,
    export_metrics_json,
)
from forecasting.models.report import (
    render_forecast_baseline_report,
    render_real_forecast_baseline_report,
)

DEFAULT_REPORT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reviews"
    / "FORECAST_BASELINE_REPORT.md"
)
REAL_REPORT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reviews"
    / "REAL_FORECAST_BASELINE_REPORT.md"
)
DEFAULT_METRICS_JSON = (
    Path(__file__).resolve().parents[1] / "data" / "forecast_models" / "baseline_metrics.json"
)
REAL_MODELS_DIR = (
    Path(__file__).resolve().parents[1] / "data" / "forecast_models" / "real_30d"
)
REAL_METRICS_JSON = REAL_MODELS_DIR / "baseline_metrics.json"
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


def _resolve_cotton_registry_id(session: Session) -> UUID:
    try:
        return RegistryService(session).get_active_config(COTTON_COMMODITY_ID).registry_id
    except RegistryNotFoundError:
        registry_id = session.execute(
            select(CommodityRegistryModel.registry_id)
            .where(CommodityRegistryModel.commodity_id == COTTON_COMMODITY_ID)
            .order_by(CommodityRegistryModel.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if registry_id is None:
            raise RegistryNotFoundError(
                f"no commodity_registry for commodity_id={COTTON_COMMODITY_ID}"
            ) from None
        return registry_id


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
        description="Train/evaluate forecast baselines (naive, linear, random forest)"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--fixture",
        action="store_true",
        help="Use PI10 deterministic fixtures (no DATABASE_URL)",
    )
    mode.add_argument(
        "--real",
        "--database-only",
        dest="real_corpus",
        action="store_true",
        help="Use exported real JSONL corpus (data/forecast_datasets/real_forecast_target_*.jsonl)",
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
        help="Inclusive as_of_date lower bound (live database mode)",
    )
    parser.add_argument(
        "--window-end",
        type=date.fromisoformat,
        default=None,
        help="Inclusive as_of_date upper bound (live database mode)",
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=None,
        help="Directory for joblib artifacts (default: real_30d or forecast_models/30d)",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write markdown report (fixture or real path when --real)",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
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
        models_dir = args.models_dir or DEFAULT_MODELS_DIR
        metrics_path = DEFAULT_METRICS_JSON
        use_horizon_subdir = True
        report_path = args.report_path or DEFAULT_REPORT
    elif args.real_corpus:
        dataset = load_real_training_dataset(horizon_days=args.horizon_days)
        models_dir = args.models_dir or REAL_MODELS_DIR
        metrics_path = REAL_METRICS_JSON
        use_horizon_subdir = False
        report_path = args.report_path or REAL_REPORT
    else:
        if not database_url:
            print(
                "DATABASE_URL required (or pass --fixture / --real)",
                file=sys.stderr,
            )
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
        models_dir = args.models_dir or DEFAULT_MODELS_DIR
        metrics_path = DEFAULT_METRICS_JSON
        use_horizon_subdir = True
        report_path = args.report_path or DEFAULT_REPORT

    results = evaluate_all_baselines(
        dataset,
        output_dir=models_dir,
        save_models=not args.no_save_models,
        use_horizon_subdir=use_horizon_subdir,
    )
    metrics_path = export_metrics_json(results, metrics_path)

    best = min(results, key=lambda r: r.metrics.rmse)
    beats = best_non_naive_beats_naive(results, metric="rmse")

    for row in results:
        m = row.metrics
        print(
            f"model={row.model_name} mae={m.mae:.4f} rmse={m.rmse:.4f} "
            f"mape_pct={m.mape_pct:.4f} folds={row.fold_count} path={row.model_path}"
        )
    print(f"best_model={best.model_name} beats_naive={'Y' if beats else 'N'}")
    print(f"metrics_json={metrics_path}")

    if args.write_report:
        if args.real_corpus:
            corpus_path = real_forecast_jsonl_path(args.horizon_days)
            report = render_real_forecast_baseline_report(
                dataset,
                results,
                workspace_ref=_git_ref(),
                corpus_path=str(corpus_path),
                models_dir=str(models_dir),
                metrics_json_path=str(metrics_path),
                pytest_count=_pytest_count(),
            )
        else:
            report = render_forecast_baseline_report(
                dataset,
                results,
                workspace_ref=_git_ref(),
                models_dir=str(models_dir),
                metrics_json_path=str(metrics_path),
                pytest_count=_pytest_count(),
            )
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(f"report={report_path}")

    if args.sync_services:
        if not database_url:
            print("--sync-services requires DATABASE_URL", file=sys.stderr)
            return 1
        engine = create_engine(database_url, pool_pre_ping=True)
        with Session(engine) as session:
            handoff = BaselineHandoffService(session)
            try:
                if args.fixture:
                    registered, quality_rows = handoff.sync_from_metrics_json(
                        metrics_path=metrics_path,
                        dataset=dataset,
                    )
                else:
                    registered, quality_rows = handoff.sync_from_metrics_json(
                        metrics_path=metrics_path,
                        dataset=dataset,
                        registry_id=_resolve_cotton_registry_id(session),
                    )
            except RegistryNotFoundError as exc:
                print(f"sync_services skipped: {exc}", file=sys.stderr)
                return 1
            session.commit()
        print(
            f"sync_services registry={len(registered)} quality_rows={len(quality_rows)}"
        )
        engine.dispose()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
