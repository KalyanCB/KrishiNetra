#!/usr/bin/env python3
"""Batch validate pending Agmarknet observations (PI8 Track A).

Transitions draft (`received`) rows to `validated` or `rejected` after
null, range, mapping, and date checks.

Usage:
    DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \\
        uv run python scripts/observation_validate.py

    uv run python scripts/observation_validate.py --dry-run --write-report
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.config.settings import get_settings
from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    SOURCE_AGMARKNET,
)
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_expected_market_ids,
)
from backend.app.services.quality.metrics import compute_overall_quality_score
from backend.app.services.quality.snapshot_service import compute_agmarknet_metrics
from backend.app.services.validation.observation_validation_service import (
    ObservationValidationService,
    render_observation_validation_report_markdown,
)
from backend.app.services.validation.weather_observation_validation_service import (
    WeatherObservationValidationService,
)

DEFAULT_REPORT = (
    Path(__file__).resolve().parents[1]
    / "docs"
    / "reviews"
    / "OBSERVATION_VALIDATION_REPORT.md"
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate pending Agmarknet observations"
    )
    parser.add_argument(
        "--commodity-id",
        default=COTTON_COMMODITY_ID,
        help="Commodity scope (default: cotton)",
    )
    parser.add_argument(
        "--source",
        default=SOURCE_AGMARKNET,
        help="Observation source filter (default: agmarknet)",
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
        "--dry-run",
        action="store_true",
        help="Run checks without updating validation_status",
    )
    parser.add_argument(
        "--write-report",
        action="store_true",
        help=f"Write markdown report (default: {DEFAULT_REPORT.name})",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT,
        help="Report output path when --write-report is set",
    )
    parser.add_argument(
        "--refresh-snapshot",
        action="store_true",
        help="Refresh data_quality_snapshot after validation",
    )
    parser.add_argument(
        "--include-weather",
        action="store_true",
        help="Also validate pending NASA POWER weather rows (parallel E-03 path)",
    )
    return parser.parse_args()


def _estimate_dqs_impact(
    session: Session,
    *,
    validated_count: int,
    rejected_count: int,
    window_start: date | None,
    window_end: date | None,
) -> tuple[float, float, float, float]:
    """Return penalty/score before and after validation (approximate)."""
    anchor = window_end or date.today()
    window_start_resolved = window_start or anchor.replace(year=anchor.year - 1)
    metrics = compute_agmarknet_metrics(
        session,
        window_start=window_start_resolved,
        window_end=anchor,
        expected_market_ids=load_expected_market_ids(),
        now=datetime.now(UTC),
    )
    row_count = max(
        1,
        metrics.days_with_data * max(1, metrics.markets_reporting),
    )
    penalty_before = min(0.3, metrics.anomaly_count / row_count)
    score_before = float(
        compute_overall_quality_score(
            coverage_ratio=metrics.coverage_ratio,
            completeness_ratio=metrics.completeness_ratio,
            lag_hours_value=metrics.agmarknet_lag_hours,
            anomaly_count=metrics.anomaly_count,
            row_count=row_count,
        )
    )
    anomalies_after = max(0, metrics.anomaly_count - validated_count) + rejected_count
    penalty_after = min(0.3, anomalies_after / row_count)
    score_after = float(
        compute_overall_quality_score(
            coverage_ratio=metrics.coverage_ratio,
            completeness_ratio=metrics.completeness_ratio,
            lag_hours_value=metrics.agmarknet_lag_hours,
            anomaly_count=anomalies_after,
            row_count=row_count,
        )
    )
    return penalty_before, penalty_after, score_before, score_after


def main() -> int:
    args = _parse_args()
    db_url = os.environ.get("DATABASE_URL") or get_settings().database_url
    if not db_url:
        print("DATABASE_URL required", file=sys.stderr)
        return 1

    engine = create_engine(db_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            service = ObservationValidationService(session)
            pre_price, pre_arrival = service.count_pending(
                commodity_id=args.commodity_id,
                source=args.source,
                window_start=args.window_start,
                window_end=args.window_end,
            )
            result = service.validate_pending(
                commodity_id=args.commodity_id,
                source=args.source,
                window_start=args.window_start,
                window_end=args.window_end,
                dry_run=args.dry_run,
            )
            weather_result = None
            pre_weather = 0
            if args.include_weather:
                weather_service = WeatherObservationValidationService(session)
                pre_weather = weather_service.count_pending(
                    commodity_id=args.commodity_id,
                    window_start=args.window_start,
                    window_end=args.window_end,
                )
                weather_result = weather_service.validate_pending(
                    commodity_id=args.commodity_id,
                    window_start=args.window_start,
                    window_end=args.window_end,
                    dry_run=args.dry_run,
                )
            penalty_before, penalty_after, score_before, score_after = (
                _estimate_dqs_impact(
                    session,
                    validated_count=result.total_validated,
                    rejected_count=result.total_rejected,
                    window_start=args.window_start,
                    window_end=args.window_end,
                )
            )

            if args.write_report:
                report = render_observation_validation_report_markdown(
                    result=result,
                    commodity_id=args.commodity_id,
                    source=args.source,
                    window_start=args.window_start,
                    window_end=args.window_end,
                    dry_run=args.dry_run,
                    pre_pending_price=pre_price,
                    pre_pending_arrival=pre_arrival,
                    expected_penalty_before=penalty_before,
                    expected_penalty_after=penalty_after,
                    expected_score_before=score_before,
                    expected_score_after=score_after,
                )
                args.report_path.parent.mkdir(parents=True, exist_ok=True)
                args.report_path.write_text(report, encoding="utf-8")

            if args.refresh_snapshot and not args.dry_run:
                from backend.app.services.quality.snapshot_service import (
                    DataQualitySnapshotService,
                )

                anchor = args.window_end or date.today()
                DataQualitySnapshotService(session).record_after_agmarknet_ingest(
                    commodity_id=args.commodity_id,
                    as_of_date=anchor,
                )

            if not args.dry_run:
                session.commit()
    except Exception as exc:
        print(f"Observation validation failed: {exc}", file=sys.stderr)
        return 1
    finally:
        engine.dispose()

    payload = {
        "service": "backend/app/services/validation/observation_validation_service.py",
        "cli": "scripts/observation_validate.py",
        "dry_run": args.dry_run,
        "pending_before": {
            "price_observation": pre_price,
            "arrival_observation": pre_arrival,
        },
        "examined": result.total_examined,
        "validated": result.total_validated,
        "rejected": result.total_rejected,
        "price": {
            "examined": result.price.examined,
            "validated": result.price.validated,
            "rejected": result.price.rejected,
            "issue_counts": result.price.issue_counts,
        },
        "arrival": {
            "examined": result.arrival.examined,
            "validated": result.arrival.validated,
            "rejected": result.arrival.rejected,
            "issue_counts": result.arrival.issue_counts,
        },
        "weather": (
            {
                "pending_before": pre_weather,
                "examined": weather_result.weather.examined,
                "validated": weather_result.weather.validated,
                "rejected": weather_result.weather.rejected,
                "issue_counts": weather_result.weather.issue_counts,
            }
            if weather_result is not None
            else None
        ),
        "dqs_impact": {
            "anomaly_penalty_before": round(penalty_before, 4),
            "anomaly_penalty_after": round(penalty_after, 4),
            "penalty_reduction": round(penalty_before - penalty_after, 4),
            "overall_quality_score_before": round(score_before, 4),
            "overall_quality_score_after": round(score_after, 4),
        },
        "report_path": str(args.report_path) if args.write_report else None,
    }
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
