"""Batch observation validation service (PI8 Track A)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from uuid import UUID

from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import (
    DRAFT_VALIDATION_STATUS,
    ArrivalObservationModel,
    ObservationValidationStatus,
    PriceObservationModel,
)
from backend.app.persistence.models.reference import (
    CommodityModel,
    MarketModel,
)
from backend.app.persistence.validation.agmarknet_observation import (
    ValidationIssue,
    validate_arrival_observation_fields,
    validate_price_observation_fields,
)
from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    SOURCE_AGMARKNET,
)

PENDING_VALIDATION_STATUSES = frozenset({DRAFT_VALIDATION_STATUS.value})
BULK_UPDATE_CHUNK_SIZE = 2000


@dataclass(frozen=True, slots=True)
class RowValidationSummary:
    """Counts and issue breakdown for one observation table."""

    table: str
    examined: int
    validated: int
    rejected: int
    skipped: int
    issue_counts: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class BatchValidationResult:
    """Outcome of a batch validation run."""

    price: RowValidationSummary
    arrival: RowValidationSummary

    @property
    def total_examined(self) -> int:
        return self.price.examined + self.arrival.examined

    @property
    def total_validated(self) -> int:
        return self.price.validated + self.arrival.validated

    @property
    def total_rejected(self) -> int:
        return self.price.rejected + self.arrival.rejected


class ObservationValidationService:
    """Validate pending Agmarknet observations and set validated/rejected status."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def validate_pending(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        source: str = SOURCE_AGMARKNET,
        window_start: date | None = None,
        window_end: date | None = None,
        dry_run: bool = False,
    ) -> BatchValidationResult:
        """Validate received (draft) rows; update status unless dry_run."""
        known_markets, known_commodities = self._load_reference_ids()
        price_summary = self._validate_prices(
            commodity_id=commodity_id,
            source=source,
            window_start=window_start,
            window_end=window_end,
            known_market_ids=known_markets,
            known_commodity_ids=known_commodities,
            dry_run=dry_run,
        )
        arrival_summary = self._validate_arrivals(
            commodity_id=commodity_id,
            source=source,
            window_start=window_start,
            window_end=window_end,
            known_market_ids=known_markets,
            known_commodity_ids=known_commodities,
            dry_run=dry_run,
        )
        return BatchValidationResult(price=price_summary, arrival=arrival_summary)

    def count_pending(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        source: str = SOURCE_AGMARKNET,
        window_start: date | None = None,
        window_end: date | None = None,
    ) -> tuple[int, int]:
        """Return (price_pending, arrival_pending) without mutating rows."""
        price_filters = [
            PriceObservationModel.source == source,
            PriceObservationModel.commodity_id == commodity_id,
            PriceObservationModel.validation_status.in_(PENDING_VALIDATION_STATUSES),
        ]
        arrival_filters = [
            ArrivalObservationModel.source == source,
            ArrivalObservationModel.commodity_id == commodity_id,
            ArrivalObservationModel.validation_status.in_(PENDING_VALIDATION_STATUSES),
        ]
        if window_start is not None:
            price_filters.append(PriceObservationModel.as_of_date >= window_start)
            arrival_filters.append(ArrivalObservationModel.as_of_date >= window_start)
        if window_end is not None:
            price_filters.append(PriceObservationModel.as_of_date <= window_end)
            arrival_filters.append(ArrivalObservationModel.as_of_date <= window_end)
        price_count = int(
            self._session.scalar(
                select(func.count()).select_from(PriceObservationModel).where(*price_filters)
            )
            or 0
        )
        arrival_count = int(
            self._session.scalar(
                select(func.count())
                .select_from(ArrivalObservationModel)
                .where(*arrival_filters)
            )
            or 0
        )
        return price_count, arrival_count

    def _load_reference_ids(self) -> tuple[frozenset[str], frozenset[str]]:
        market_ids = frozenset(
            self._session.scalars(select(MarketModel.market_id)).all()
        )
        commodity_ids = frozenset(
            self._session.scalars(select(CommodityModel.commodity_id)).all()
        )
        return market_ids, commodity_ids

    def _validate_prices(
        self,
        *,
        commodity_id: str,
        source: str,
        window_start: date | None,
        window_end: date | None,
        known_market_ids: frozenset[str],
        known_commodity_ids: frozenset[str],
        dry_run: bool,
    ) -> RowValidationSummary:
        stmt = self._pending_price_stmt(
            commodity_id=commodity_id,
            source=source,
            window_start=window_start,
            window_end=window_end,
        )
        rows = list(self._session.scalars(stmt).all())
        validated = 0
        rejected = 0
        issue_counts: dict[str, int] = {}

        validated_ids: list[UUID] = []
        rejected_ids: list[UUID] = []

        for row in rows:
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
                known_market_ids=known_market_ids,
                known_commodity_ids=known_commodity_ids,
            )
            if outcome.passed:
                validated += 1
                validated_ids.append(row.observation_id)
            else:
                rejected += 1
                _accumulate_issues(issue_counts, outcome.issues)
                rejected_ids.append(row.observation_id)

        if not dry_run:
            self._bulk_set_price_status(
                validated_ids, ObservationValidationStatus.VALIDATED.value
            )
            self._bulk_set_price_status(
                rejected_ids, ObservationValidationStatus.REJECTED.value
            )
            self._session.flush()

        return RowValidationSummary(
            table="price_observation",
            examined=len(rows),
            validated=validated,
            rejected=rejected,
            skipped=0,
            issue_counts=issue_counts,
        )

    def _validate_arrivals(
        self,
        *,
        commodity_id: str,
        source: str,
        window_start: date | None,
        window_end: date | None,
        known_market_ids: frozenset[str],
        known_commodity_ids: frozenset[str],
        dry_run: bool,
    ) -> RowValidationSummary:
        stmt = self._pending_arrival_stmt(
            commodity_id=commodity_id,
            source=source,
            window_start=window_start,
            window_end=window_end,
        )
        rows = list(self._session.scalars(stmt).all())
        validated = 0
        rejected = 0
        issue_counts: dict[str, int] = {}

        validated_ids: list[UUID] = []
        rejected_ids: list[UUID] = []

        for row in rows:
            outcome = validate_arrival_observation_fields(
                market_id=row.market_id,
                commodity_id=row.commodity_id,
                volume=row.volume,
                unit=row.unit,
                observed_at=row.observed_at,
                as_of_date=row.as_of_date,
                source=row.source,
                known_market_ids=known_market_ids,
                known_commodity_ids=known_commodity_ids,
            )
            if outcome.passed:
                validated += 1
                validated_ids.append(row.observation_id)
            else:
                rejected += 1
                _accumulate_issues(issue_counts, outcome.issues)
                rejected_ids.append(row.observation_id)

        if not dry_run:
            self._bulk_set_arrival_status(
                validated_ids, ObservationValidationStatus.VALIDATED.value
            )
            self._bulk_set_arrival_status(
                rejected_ids, ObservationValidationStatus.REJECTED.value
            )
            self._session.flush()

        return RowValidationSummary(
            table="arrival_observation",
            examined=len(rows),
            validated=validated,
            rejected=rejected,
            skipped=0,
            issue_counts=issue_counts,
        )

    @staticmethod
    def _pending_price_stmt(
        *,
        commodity_id: str,
        source: str,
        window_start: date | None,
        window_end: date | None,
    ) -> Select[tuple[PriceObservationModel]]:
        stmt = select(PriceObservationModel).where(
            PriceObservationModel.source == source,
            PriceObservationModel.commodity_id == commodity_id,
            PriceObservationModel.validation_status.in_(PENDING_VALIDATION_STATUSES),
        )
        if window_start is not None:
            stmt = stmt.where(PriceObservationModel.as_of_date >= window_start)
        if window_end is not None:
            stmt = stmt.where(PriceObservationModel.as_of_date <= window_end)
        return stmt.order_by(PriceObservationModel.as_of_date)

    @staticmethod
    def _pending_arrival_stmt(
        *,
        commodity_id: str,
        source: str,
        window_start: date | None,
        window_end: date | None,
    ) -> Select[tuple[ArrivalObservationModel]]:
        stmt = select(ArrivalObservationModel).where(
            ArrivalObservationModel.source == source,
            ArrivalObservationModel.commodity_id == commodity_id,
            ArrivalObservationModel.validation_status.in_(PENDING_VALIDATION_STATUSES),
        )
        if window_start is not None:
            stmt = stmt.where(ArrivalObservationModel.as_of_date >= window_start)
        if window_end is not None:
            stmt = stmt.where(ArrivalObservationModel.as_of_date <= window_end)
        return stmt.order_by(ArrivalObservationModel.as_of_date)

    def _bulk_set_price_status(self, observation_ids: list[UUID], status: str) -> None:
        for offset in range(0, len(observation_ids), BULK_UPDATE_CHUNK_SIZE):
            chunk = observation_ids[offset : offset + BULK_UPDATE_CHUNK_SIZE]
            if not chunk:
                continue
            self._session.execute(
                update(PriceObservationModel)
                .where(PriceObservationModel.observation_id.in_(chunk))
                .values(validation_status=status)
            )

    def _bulk_set_arrival_status(self, observation_ids: list[UUID], status: str) -> None:
        for offset in range(0, len(observation_ids), BULK_UPDATE_CHUNK_SIZE):
            chunk = observation_ids[offset : offset + BULK_UPDATE_CHUNK_SIZE]
            if not chunk:
                continue
            self._session.execute(
                update(ArrivalObservationModel)
                .where(ArrivalObservationModel.observation_id.in_(chunk))
                .values(validation_status=status)
            )


def _accumulate_issues(counts: dict[str, int], issues: tuple[ValidationIssue, ...]) -> None:
    for issue in issues:
        counts[issue.check] = counts.get(issue.check, 0) + 1


def render_observation_validation_report_markdown(
    *,
    result: BatchValidationResult,
    commodity_id: str,
    source: str,
    window_start: date | None,
    window_end: date | None,
    dry_run: bool,
    pre_pending_price: int,
    pre_pending_arrival: int,
    expected_penalty_before: float,
    expected_penalty_after: float,
    expected_score_before: float,
    expected_score_after: float,
) -> str:
    """Render PI8 Track A report body."""
    window_label = (
        f"{window_start.isoformat()} → {window_end.isoformat()}"
        if window_start and window_end
        else "all dates"
    )
    lines = [
        "# Observation Validation Report — PI8 Track A",
        "",
        "**Date:** 2026-06-04",
        "**PI:** PI8 Track A (KDO — observation validation pipeline)",
        f"**Mode:** {'dry-run' if dry_run else 'commit'}",
        "",
        "---",
        "",
        "## 1. Executive summary",
        "",
        "| Question | Answer |",
        "|----------|--------|",
        f"| Commodity / source | `{commodity_id}` / `{source}` |",
        f"| Window | {window_label} |",
        f"| Pending before run (price / arrival) | **{pre_pending_price}** / **{pre_pending_arrival}** |",
        f"| Rows examined | **{result.total_examined}** |",
        f"| Validated | **{result.total_validated}** |",
        f"| Rejected | **{result.total_rejected}** |",
        "",
        "### Workflow statuses",
        "",
        "| Workflow | DB enum |",
        "|----------|---------|",
        "| draft (pending QA) | `received` |",
        "| validated | `validated` |",
        "| rejected | `rejected` |",
        "",
        "---",
        "",
        "## 2. Validation checks",
        "",
        "| Check | Price | Arrival |",
        "|-------|-------|---------|",
        "| Null required fields | yes | yes |",
        "| Price range (INR/quintal) | yes | — |",
        "| Arrival volume range | — | yes |",
        "| Commodity registry mapping | yes | yes |",
        "| Market registry mapping | yes | yes |",
        "| Date consistency (`observed_at` vs `as_of_date`) | yes | yes |",
        "",
        "---",
        "",
        "## 3. Run breakdown",
        "",
        "### 3.1 Price observations",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Examined | {result.price.examined} |",
        f"| Validated | {result.price.validated} |",
        f"| Rejected | {result.price.rejected} |",
        "",
    ]
    if result.price.issue_counts:
        lines.extend(["**Rejection reasons:**", ""])
        for check, count in sorted(result.price.issue_counts.items()):
            lines.append(f"- `{check}`: {count}")
        lines.append("")

    lines.extend(
        [
            "### 3.2 Arrival observations",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Examined | {result.arrival.examined} |",
            f"| Validated | {result.arrival.validated} |",
            f"| Rejected | {result.arrival.rejected} |",
            "",
        ]
    )
    if result.arrival.issue_counts:
        lines.extend(["**Rejection reasons:**", ""])
        for check, count in sorted(result.arrival.issue_counts.items()):
            lines.append(f"- `{check}`: {count}")
        lines.append("")

    lines.extend(
        [
            "---",
            "",
            "## 4. DQS impact (anomaly penalty)",
            "",
            "Non-`validated` / non-`published` rows count as anomalies in "
            "`compute_overall_quality_score` (cap 0.30).",
            "",
            "| Metric | Before | After (expected) |",
            "|--------|--------|------------------|",
            f"| Anomaly penalty | **{expected_penalty_before:.4f}** | **{expected_penalty_after:.4f}** |",
            f"| Overall quality score (belt, fixed coverage) | **{expected_score_before:.4f}** | **{expected_score_after:.4f}** |",
            "",
            f"**Penalty reduction:** **{expected_penalty_before - expected_penalty_after:.4f}**",
            "",
            "---",
            "",
            "## 5. Deliverables",
            "",
            "| Artifact | Path |",
            "|----------|------|",
            "| Validation service | `backend/app/services/validation/observation_validation_service.py` |",
            "| Field validators | `backend/app/persistence/validation/agmarknet_observation.py` |",
            "| Batch CLI | `scripts/observation_validate.py` |",
            "| Migration (`rejected`) | `backend/app/persistence/migrations/versions/0011_observation_validation_rejected.py` |",
            "",
            "---",
            "",
            "*End of PI8 Track A observation validation report.*",
        ]
    )
    return "\n".join(lines) + "\n"
