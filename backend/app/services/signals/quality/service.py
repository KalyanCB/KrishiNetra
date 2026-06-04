"""SignalQualityService — PI9 Track E signal coverage and confidence tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.models.signal import (
    SignalSnapshotModel,
    StructuredSignalModel,
)
from backend.app.persistence.repositories.signal import (
    SignalSnapshotRepository,
    StructuredSignalRepository,
)
from backend.app.services.registry.service import RegistryService
from backend.app.services.signals.quality.metrics import (
    SignalQualityMetrics,
    build_signal_quality_metrics,
)


@dataclass(frozen=True, slots=True)
class SignalQualityResult:
    """Outcome of a signal quality assessment."""

    metrics: SignalQualityMetrics
    commodity_id: str
    as_of_date: date
    registry_id: UUID


class SignalQualityService:
    """Assess structured_signal + signal_snapshot coverage and confidence."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._signal_repo = StructuredSignalRepository(session)
        self._snapshot_repo = SignalSnapshotRepository(session)
        self._registry = RegistryService(session)

    def assess(
        self,
        *,
        commodity_id: str = "cotton",
        as_of_date: date | None = None,
        registry: CommodityRegistryModel | None = None,
        now: datetime | None = None,
    ) -> SignalQualityResult:
        """Compute signal quality metrics for one commodity/day."""
        anchor = as_of_date or date.today()
        clock = now or datetime.now(tz=UTC)
        active = registry or self._registry.get_active_config(commodity_id)
        metrics = compute_signal_quality_metrics(
            self._session,
            commodity_id=commodity_id,
            as_of_date=anchor,
            registry=active,
            now=clock,
        )
        return SignalQualityResult(
            metrics=metrics,
            commodity_id=commodity_id,
            as_of_date=anchor,
            registry_id=active.registry_id,
        )


def compute_signal_quality_metrics(
    session: Session,
    *,
    commodity_id: str,
    as_of_date: date,
    registry: CommodityRegistryModel,
    now: datetime,
) -> SignalQualityMetrics:
    """Query structured_signal + signal_snapshot and assemble metrics."""
    signal_repo = StructuredSignalRepository(session)
    snapshot_repo = SignalSnapshotRepository(session)

    signals = signal_repo.list_by_commodity_date(
        commodity_id,
        as_of_date,
        registry_id=registry.registry_id,
    )
    snapshot = snapshot_repo.get_snapshot(
        commodity_id,
        as_of_date,
        registry_id=registry.registry_id,
    )
    return _metrics_from_rows(
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry=registry,
        signals=signals,
        snapshot=snapshot,
        now=now,
    )


def _metrics_from_rows(
    *,
    commodity_id: str,
    as_of_date: date,
    registry: CommodityRegistryModel,
    signals: list[StructuredSignalModel],
    snapshot: SignalSnapshotModel | None,
    now: datetime,
) -> SignalQualityMetrics:
    agent_confidences = {row.agent_type: row.confidence for row in signals}
    latest_ts = max((row.as_of_timestamp for row in signals), default=None)
    snapshot_count = len(snapshot.signal_ids) if snapshot is not None else 0
    return build_signal_quality_metrics(
        commodity_id=commodity_id,
        as_of_date=as_of_date,
        registry_id=registry.registry_id,
        agent_confidences=agent_confidences,
        required_agents=list(registry.required_agents),
        optional_agents=registry.optional_agents,
        latest_as_of_timestamp=latest_ts,
        snapshot_signal_count=snapshot_count,
        snapshot_present=snapshot is not None,
        snapshot_hash=snapshot.snapshot_hash if snapshot is not None else None,
        now=now,
    )


def render_signal_quality_report_markdown(
    *,
    result: SignalQualityResult,
) -> str:
    """Render PI9 Track E report body for docs/reviews/SIGNAL_QUALITY_REPORT.md."""
    metrics = result.metrics
    conf = metrics.confidence
    lines = [
        "# Signal Quality Report — PI9 Track E",
        "",
        "**Date:** 2026-06-04",
        "**PI:** PI9 Track E (KDO — `SignalQualityService`)",
        "**Status:** Signal quality assessment from `structured_signal` + `signal_snapshot`",
        "",
        "---",
        "",
        "## 1. Verdict",
        "",
        "| Question | Answer |",
        "|----------|--------|",
        f"| Commodity / `as_of_date` | `{result.commodity_id}` / `{result.as_of_date.isoformat()}` |",
        f"| Active `registry_id` (FK) | `{result.registry_id}` |",
        f"| `signal_count` (structured rows) | **{metrics.signal_count}** |",
        f"| Snapshot present? | **{'Yes' if metrics.snapshot_present else 'No'}** |",
        f"| Coverage ratio (all registry agents) | **{metrics.coverage_ratio:.4f}** |",
        f"| Required coverage ratio | **{metrics.required_coverage_ratio:.4f}** |",
        f"| Signal freshness | **`{metrics.freshness}`** |",
        f"| Mean agent confidence | **{conf.mean_confidence}** |",
        "",
        "---",
        "",
        "## 2. Coverage",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Agents present / expected | **{metrics.agents_present}** / "
        f"**{metrics.agents_expected}** |",
        f"| Required present / expected | **{metrics.required_agents_present}** / "
        f"**{metrics.required_agents_expected}** |",
        f"| `signals_missing` (required) | `{list(metrics.signals_missing)}` |",
        f"| Optional agents missing | `{list(metrics.optional_agents_missing)}` |",
        f"| Agents present | `{list(metrics.agents_present_list)}` |",
        "",
        "---",
        "",
        "## 3. Freshness",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Latest `as_of_timestamp` | `{metrics.latest_as_of_timestamp}` |",
        f"| `signal_lag_hours` | **{metrics.signal_lag_hours}** |",
        f"| Freshness classification | **`{metrics.freshness}`** |",
        "",
        "---",
        "",
        "## 4. Confidence aggregates",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Count | **{conf.count}** |",
        f"| Min | **{conf.min_confidence}** |",
        f"| Max | **{conf.max_confidence}** |",
        f"| Mean | **{conf.mean_confidence}** |",
        "",
        "---",
        "",
        "## 5. Snapshot alignment",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| `snapshot_signal_count` | **{metrics.snapshot_signal_count}** |",
        f"| Snapshot aligned with structured rows? | **{metrics.snapshot_aligned}** |",
        f"| `snapshot_hash` | `{metrics.snapshot_hash}` |",
        "",
        "---",
        "",
        "## 6. Deliverables",
        "",
        "| Artifact | Path |",
        "|----------|------|",
        "| Signal quality service | `backend/app/services/signals/quality/service.py` |",
        "| Metrics helpers | `backend/app/services/signals/quality/metrics.py` |",
        "| Unit tests | `tests/unit/test_signal_quality.py` |",
        "",
        "---",
        "",
        "## 7. Sample metrics payload",
        "",
        "```json",
    ]
    import json

    lines.append(json.dumps(metrics.to_report_detail(), indent=2))
    lines.extend(["```", ""])
    return "\n".join(lines)


__all__ = [
    "SignalQualityResult",
    "SignalQualityService",
    "compute_signal_quality_metrics",
    "render_signal_quality_report_markdown",
]
