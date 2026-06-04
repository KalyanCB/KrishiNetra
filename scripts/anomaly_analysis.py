#!/usr/bin/env python3
"""PI8 Track B: Classify Agmarknet observation anomalies for DQS penalty analysis.

Usage:
    DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \\
        uv run python scripts/anomaly_analysis.py

    uv run python scripts/anomaly_analysis.py --json
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import date

from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    PriceObservationModel,
)
from backend.app.persistence.validation.agmarknet_observation import (
    validate_arrival_observation_fields,
    validate_price_observation_fields,
)
from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    SOURCE_AGMARKNET,
)
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_expected_market_ids,
)
from backend.app.services.quality.metrics import (
    VALID_VALIDATION_STATUSES,
    compute_overall_quality_score,
)

DEFAULT_WINDOW_START = date(2023, 6, 1)
DEFAULT_WINDOW_END = date(2026, 6, 3)


@dataclass(frozen=True, slots=True)
class RowClassification:
    table: str
    observation_id: str
    market_id: str
    as_of_date: str
    validation_status: str
    categories: tuple[str, ...]
    issue_checks: tuple[str, ...]


@dataclass
class AnomalyAnalysisResult:
    window_start: str
    window_end: str
    price_rows: int
    arrival_rows: int
    total_rows: int
    dqs_anomaly_count: int
    markets_reporting: int
    markets_expected: int
    validation_status_breakdown: dict[str, int]
    category_counts: dict[str, int]
    category_row_counts: dict[str, int]
    duplicate_price_keys: int
    duplicate_price_extra_rows: int
    duplicate_arrival_keys: int
    duplicate_arrival_extra_rows: int
    price_type_breakdown: dict[str, int]
    market_breakdown: dict[str, int]
    quality_grade_null_price: int
    non_validated_only: int
    projected_score_if_validated: str
    top_fix: str
    sample_rows: list[dict] = field(default_factory=list)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-date", type=date.fromisoformat, default=DEFAULT_WINDOW_START)
    parser.add_argument("--end-date", type=date.fromisoformat, default=DEFAULT_WINDOW_END)
    parser.add_argument("--json", action="store_true", help="Emit JSON to stdout")
    return parser.parse_args()


def _category_from_check(check: str) -> str:
    if check == "null_fields":
        return "missing_fields"
    if check in ("market_mapping", "commodity_mapping", "source"):
        return "mapping_failures"
    if check in ("date_consistency",):
        return "stale_observations"
    if check in ("price_range", "arrival_range"):
        return "value_range"
    return "other_validation"


def _load_rows(session: Session, *, window_start: date, window_end: date) -> tuple[list, list]:
    market_ids = load_expected_market_ids()
    price_stmt = select(PriceObservationModel).where(
        PriceObservationModel.source == SOURCE_AGMARKNET,
        PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
        PriceObservationModel.market_id.in_(market_ids),
        PriceObservationModel.as_of_date >= window_start,
        PriceObservationModel.as_of_date <= window_end,
    )
    arrival_stmt = select(ArrivalObservationModel).where(
        ArrivalObservationModel.source == SOURCE_AGMARKNET,
        ArrivalObservationModel.commodity_id == COTTON_COMMODITY_ID,
        ArrivalObservationModel.market_id.in_(market_ids),
        ArrivalObservationModel.as_of_date >= window_start,
        ArrivalObservationModel.as_of_date <= window_end,
    )
    return list(session.scalars(price_stmt)), list(session.scalars(arrival_stmt))


def _duplicate_stats(session: Session, *, window_start: date, window_end: date) -> dict[str, int]:
    dup_sql = text(
        """
        SELECT
          (SELECT COUNT(*) FROM (
             SELECT market_id, as_of_date, price_type, COUNT(*) AS cnt
             FROM price_observation
             WHERE source = :source AND commodity_id = :commodity
               AND as_of_date BETWEEN :ws AND :we
             GROUP BY market_id, as_of_date, price_type
             HAVING COUNT(*) > 1
           ) d) AS price_dup_keys,
          (SELECT COALESCE(SUM(cnt - 1), 0) FROM (
             SELECT COUNT(*) AS cnt
             FROM price_observation
             WHERE source = :source AND commodity_id = :commodity
               AND as_of_date BETWEEN :ws AND :we
             GROUP BY market_id, as_of_date, price_type
             HAVING COUNT(*) > 1
           ) d) AS price_dup_extra,
          (SELECT COUNT(*) FROM (
             SELECT market_id, as_of_date, COUNT(*) AS cnt
             FROM arrival_observation
             WHERE source = :source AND commodity_id = :commodity
               AND as_of_date BETWEEN :ws AND :we
             GROUP BY market_id, as_of_date
             HAVING COUNT(*) > 1
           ) d) AS arrival_dup_keys,
          (SELECT COALESCE(SUM(cnt - 1), 0) FROM (
             SELECT COUNT(*) AS cnt
             FROM arrival_observation
             WHERE source = :source AND commodity_id = :commodity
               AND as_of_date BETWEEN :ws AND :we
             GROUP BY market_id, as_of_date
             HAVING COUNT(*) > 1
           ) d) AS arrival_dup_extra
        """
    )
    row = session.execute(
        dup_sql,
        {
            "source": SOURCE_AGMARKNET,
            "commodity": COTTON_COMMODITY_ID,
            "ws": window_start,
            "we": window_end,
        },
    ).mappings().one()
    return dict(row)


def analyze(session: Session, *, window_start: date, window_end: date) -> AnomalyAnalysisResult:
    expected_markets = load_expected_market_ids()
    known_markets = frozenset(expected_markets)
    known_commodities = frozenset({COTTON_COMMODITY_ID})

    prices, arrivals = _load_rows(session, window_start=window_start, window_end=window_end)
    dup = _duplicate_stats(session, window_start=window_start, window_end=window_end)

    classifications: list[RowClassification] = []
    category_row_counts: Counter[str] = Counter()
    issue_check_counts: Counter[str] = Counter()
    validation_status_counts: Counter[str] = Counter()
    price_type_counts: Counter[str] = Counter()
    market_counts: Counter[str] = Counter()
    quality_grade_null = 0

    for row in prices:
        validation_status_counts[row.validation_status] += 1
        price_type_counts[row.price_type] += 1
        market_counts[row.market_id] += 1
        if row.quality_grade is None:
            quality_grade_null += 1

        outcome = validate_price_observation_fields(
            market_id=row.market_id,
            commodity_id=row.commodity_id,
            price_type=row.price_type,
            value=row.value,
            unit=row.unit,
            currency=row.currency,
            observed_at=row.observed_at,
            as_of_date=row.as_of_date,
            source=row.source,
            known_market_ids=known_markets,
            known_commodity_ids=known_commodities,
        )
        categories: list[str] = []
        issue_checks: list[str] = []
        for issue in outcome.issues:
            cat = _category_from_check(issue.check)
            categories.append(cat)
            issue_checks.append(issue.check)
            issue_check_counts[issue.check] += 1

        if row.validation_status not in VALID_VALIDATION_STATUSES:
            categories.append("non_validated_status")
            issue_checks.append("validation_status")

        if not categories:
            categories = ["clean_data_pending_validation"]

        for cat in set(categories):
            category_row_counts[cat] += 1

        classifications.append(
            RowClassification(
                table="price",
                observation_id=str(row.observation_id),
                market_id=row.market_id,
                as_of_date=row.as_of_date.isoformat(),
                validation_status=row.validation_status,
                categories=tuple(sorted(set(categories))),
                issue_checks=tuple(issue_checks),
            )
        )

    for row in arrivals:
        validation_status_counts[row.validation_status] += 1
        market_counts[row.market_id] += 1

        outcome = validate_arrival_observation_fields(
            market_id=row.market_id,
            commodity_id=row.commodity_id,
            volume=row.volume,
            unit=row.unit,
            observed_at=row.observed_at,
            as_of_date=row.as_of_date,
            source=row.source,
            known_market_ids=known_markets,
            known_commodity_ids=known_commodities,
        )
        categories = []
        issue_checks = []
        for issue in outcome.issues:
            cat = _category_from_check(issue.check)
            categories.append(cat)
            issue_checks.append(issue.check)
            issue_check_counts[issue.check] += 1

        if row.validation_status not in VALID_VALIDATION_STATUSES:
            categories.append("non_validated_status")
            issue_checks.append("validation_status")

        if not categories:
            categories = ["clean_data_pending_validation"]

        for cat in set(categories):
            category_row_counts[cat] += 1

        classifications.append(
            RowClassification(
                table="arrival",
                observation_id=str(row.observation_id),
                market_id=row.market_id,
                as_of_date=row.as_of_date.isoformat(),
                validation_status=row.validation_status,
                categories=tuple(sorted(set(categories))),
                issue_checks=tuple(issue_checks),
            )
        )

    if dup["price_dup_extra"] > 0:
        category_row_counts["duplicate_observations"] += int(dup["price_dup_extra"])
    if dup["arrival_dup_extra"] > 0:
        category_row_counts["duplicate_observations"] += int(dup["arrival_dup_extra"])

    total = len(prices) + len(arrivals)
    dqs_anomaly = sum(
        1
        for c in classifications
        if c.validation_status not in VALID_VALIDATION_STATUSES
    )

    latest_as_of = max(
        (date.fromisoformat(c.as_of_date) for c in classifications),
        default=None,
    )
    markets_reporting = 0
    if latest_as_of:
        markets_reporting = session.scalar(
            select(func.count(func.distinct(PriceObservationModel.market_id))).where(
                PriceObservationModel.source == SOURCE_AGMARKNET,
                PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
                PriceObservationModel.market_id.in_(expected_markets),
                PriceObservationModel.as_of_date == latest_as_of,
            )
        ) or 0

    window_days = (window_end - window_start).days + 1
    days_with_data = session.scalar(
        select(func.count(func.distinct(PriceObservationModel.as_of_date))).where(
            PriceObservationModel.source == SOURCE_AGMARKNET,
            PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
            PriceObservationModel.market_id.in_(expected_markets),
            PriceObservationModel.as_of_date >= window_start,
            PriceObservationModel.as_of_date <= window_end,
        )
    ) or 0

    coverage = markets_reporting / len(expected_markets) if expected_markets else 0.0
    completeness = days_with_data / window_days if window_days else 0.0
    row_count_proxy = max(days_with_data * max(markets_reporting, 1), 1)

    current_score = compute_overall_quality_score(
        coverage_ratio=coverage,
        completeness_ratio=completeness,
        lag_hours_value=9.0,
        anomaly_count=dqs_anomaly,
        row_count=row_count_proxy,
    )
    validated_score = compute_overall_quality_score(
        coverage_ratio=coverage,
        completeness_ratio=completeness,
        lag_hours_value=9.0,
        anomaly_count=0,
        row_count=row_count_proxy,
    )

    non_validated_only = category_row_counts.get("non_validated_status", 0)

    top_fix = (
        "Wire post-ingest validation to promote field-clean `received` rows to "
        f"`validated` — {non_validated_only}/{total} rows ({100*non_validated_only/total:.1f}%) "
        f"carry only lifecycle status gap; drops anomaly penalty from 0.30 to ~0.00 "
        f"(score {current_score} → {validated_score})."
    )

    samples = []
    for cat in (
        "non_validated_status",
        "missing_fields",
        "mapping_failures",
        "stale_observations",
        "duplicate_observations",
    ):
        for c in classifications:
            if cat in c.categories:
                samples.append(asdict(c))
                break

    return AnomalyAnalysisResult(
        window_start=window_start.isoformat(),
        window_end=window_end.isoformat(),
        price_rows=len(prices),
        arrival_rows=len(arrivals),
        total_rows=total,
        dqs_anomaly_count=dqs_anomaly,
        markets_reporting=int(markets_reporting),
        markets_expected=len(expected_markets),
        validation_status_breakdown=dict(validation_status_counts),
        category_counts=dict(issue_check_counts),
        category_row_counts=dict(category_row_counts),
        duplicate_price_keys=int(dup["price_dup_keys"]),
        duplicate_price_extra_rows=int(dup["price_dup_extra"]),
        duplicate_arrival_keys=int(dup["arrival_dup_keys"]),
        duplicate_arrival_extra_rows=int(dup["arrival_dup_extra"]),
        price_type_breakdown=dict(price_type_counts),
        market_breakdown=dict(market_counts),
        quality_grade_null_price=quality_grade_null,
        non_validated_only=non_validated_only,
        projected_score_if_validated=str(validated_score),
        top_fix=top_fix,
        sample_rows=samples,
    )


def main() -> int:
    args = _parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 1

    engine = create_engine(url)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        result = analyze(
            session,
            window_start=args.start_date,
            window_end=args.end_date,
        )

    if args.json:
        print(json.dumps(asdict(result), indent=2))
    else:
        print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
