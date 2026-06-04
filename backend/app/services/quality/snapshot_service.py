"""Persist data_quality_snapshot rows after E-03 ingest (PI6 Track E)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    PriceObservationModel,
)
from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.models.weather import WeatherObservationModel
from backend.app.persistence.repositories.quality import DataQualitySnapshotRepository
from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    SOURCE_AGMARKNET,
)
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_expected_market_ids,
)
from backend.app.services.ingest.weather.constants import (
    COTTON_COMMODITY_ID as WEATHER_COTTON_ID,
)
from backend.app.services.ingest.weather.constants import (
    DISTRICT_REGION_IDS,
    WEATHER_SOURCE_NASA_POWER,
)
from backend.app.services.quality.metrics import (
    DEFAULT_WINDOW_DAYS,
    VALID_VALIDATION_STATUSES,
    AgmarknetQualityMetrics,
    WeatherQualityMetrics,
    classify_source_health,
    completeness_ratio,
    compute_overall_quality_score,
    confidence_penalty_from_score,
    coverage_ratio,
    default_quality_window,
    lag_hours,
)
from backend.app.services.registry.service import RegistryService


@dataclass(frozen=True, slots=True)
class QualitySnapshotResult:
    """Outcome of a quality snapshot write."""

    quality_snapshot_id: UUID
    commodity_id: str
    as_of_date: date
    registry_id: UUID
    overall_quality_score: Decimal
    agmarknet_lag_hours: Decimal | None
    source_health: dict


class DataQualitySnapshotService:
    """Compute and upsert per-refresh data_quality_snapshot for cotton."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = DataQualitySnapshotRepository(session)
        self._registry = RegistryService(session)

    def record_after_agmarknet_ingest(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        as_of_date: date | None = None,
        window_days: int = DEFAULT_WINDOW_DAYS,
        expected_market_ids: tuple[str, ...] | None = None,
        now: datetime | None = None,
    ) -> QualitySnapshotResult:
        """Write or refresh snapshot after Agmarknet daily ingest or backfill."""
        anchor = as_of_date or date.today()
        window_start, window_end = default_quality_window(
            anchor, window_days=window_days
        )
        return self._record_snapshot(
            commodity_id=commodity_id,
            as_of_date=anchor,
            window_start=window_start,
            window_end=window_end,
            expected_market_ids=expected_market_ids,
            include_weather=False,
            now=now,
        )

    def record_after_agmarknet_backfill(
        self,
        *,
        window_start: date,
        window_end: date,
        commodity_id: str = COTTON_COMMODITY_ID,
        expected_market_ids: tuple[str, ...] | None = None,
        now: datetime | None = None,
    ) -> QualitySnapshotResult:
        """Write snapshot using the full backfill window for completeness."""
        return self._record_snapshot(
            commodity_id=commodity_id,
            as_of_date=window_end,
            window_start=window_start,
            window_end=window_end,
            expected_market_ids=expected_market_ids,
            include_weather=False,
            now=now,
        )

    def record_after_weather_ingest(
        self,
        *,
        commodity_id: str = WEATHER_COTTON_ID,
        as_of_date: date | None = None,
        window_start: date | None = None,
        window_end: date | None = None,
        window_days: int = DEFAULT_WINDOW_DAYS,
        now: datetime | None = None,
    ) -> QualitySnapshotResult:
        """Merge weather metrics into the daily quality snapshot (optional path)."""
        anchor = window_end or as_of_date or date.today()
        if window_start is None:
            window_start, window_end_resolved = default_quality_window(
                anchor, window_days=window_days
            )
        else:
            window_end_resolved = window_end or anchor
        return self._record_snapshot(
            commodity_id=commodity_id,
            as_of_date=anchor,
            window_start=window_start,
            window_end=window_end_resolved,
            expected_market_ids=None,
            include_weather=True,
            now=now,
        )

    def _record_snapshot(
        self,
        *,
        commodity_id: str,
        as_of_date: date,
        window_start: date,
        window_end: date,
        expected_market_ids: tuple[str, ...] | None,
        include_weather: bool,
        now: datetime | None,
    ) -> QualitySnapshotResult:
        clock = now or datetime.now(tz=UTC)
        registry = self._registry.get_active_config(commodity_id)

        markets = expected_market_ids or load_expected_market_ids()
        ag_metrics = compute_agmarknet_metrics(
            self._session,
            window_start=window_start,
            window_end=window_end,
            expected_market_ids=markets,
            now=clock,
        )
        weather_metrics: WeatherQualityMetrics | None = None
        if include_weather:
            weather_metrics = compute_weather_metrics(
                self._session,
                commodity_id=commodity_id,
                window_start=window_start,
                window_end=window_end,
                now=clock,
            )

        source_health = _build_source_health(
            ag_metrics=ag_metrics,
            weather_metrics=weather_metrics,
        )
        overall = _combined_overall_score(
            ag_metrics=ag_metrics,
            weather_metrics=weather_metrics,
        )
        penalty = confidence_penalty_from_score(overall)
        lag_decimal = (
            Decimal(str(round(ag_metrics.agmarknet_lag_hours, 2)))
            if ag_metrics.agmarknet_lag_hours is not None
            else None
        )

        entity = DataQualitySnapshotModel(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry.registry_id,
            source_health=source_health,
            overall_quality_score=overall,
            agmarknet_lag_hours=lag_decimal,
            futures_feed_ok=False,
            signals_missing=None,
            confidence_penalty_factor=penalty,
        )
        saved = self._repo.upsert_snapshot(entity)
        return QualitySnapshotResult(
            quality_snapshot_id=saved.quality_snapshot_id,
            commodity_id=saved.commodity_id,
            as_of_date=saved.as_of_date,
            registry_id=saved.registry_id,
            overall_quality_score=saved.overall_quality_score,
            agmarknet_lag_hours=saved.agmarknet_lag_hours,
            source_health=dict(saved.source_health),
        )


def compute_agmarknet_metrics(
    session: Session,
    *,
    window_start: date,
    window_end: date,
    expected_market_ids: tuple[str, ...],
    now: datetime,
) -> AgmarknetQualityMetrics:
    """Query price/arrival tables for Agmarknet quality metrics."""
    window_days = (window_end - window_start).days + 1
    latest_as_of = _max_as_of_date(
        session,
        window_start=window_start,
        window_end=window_end,
        market_ids=expected_market_ids,
    )
    markets_reporting = _markets_reporting_on_date(
        session,
        as_of_date=latest_as_of,
        market_ids=expected_market_ids,
    ) if latest_as_of else 0
    days_with_data = _distinct_days_with_price_data(
        session,
        window_start=window_start,
        window_end=window_end,
        market_ids=expected_market_ids,
    )
    latest_observed = _max_observed_at(
        session,
        window_start=window_start,
        window_end=window_end,
        market_ids=expected_market_ids,
    )
    anomaly_count = _count_anomalies(
        session,
        window_start=window_start,
        window_end=window_end,
        market_ids=expected_market_ids,
    )
    cov = coverage_ratio(markets_reporting, len(expected_market_ids))
    comp = completeness_ratio(days_with_data, window_days)
    lag = lag_hours(latest_observed, now=now)

    return AgmarknetQualityMetrics(
        markets_expected=len(expected_market_ids),
        markets_reporting=markets_reporting,
        coverage_ratio=cov,
        window_days=window_days,
        days_with_data=days_with_data,
        completeness_ratio=comp,
        latest_as_of_date=latest_as_of,
        latest_observed_at=latest_observed,
        agmarknet_lag_hours=lag,
        anomaly_count=anomaly_count,
    )


def compute_weather_metrics(
    session: Session,
    *,
    commodity_id: str,
    window_start: date,
    window_end: date,
    now: datetime,
    expected_region_ids: tuple[str, ...] | None = None,
) -> WeatherQualityMetrics:
    """Query weather_observation for belt coverage metrics."""
    regions = expected_region_ids or tuple(DISTRICT_REGION_IDS.values())
    window_days = (window_end - window_start).days + 1
    latest_as_of = _max_weather_as_of_date(
        session,
        commodity_id=commodity_id,
        window_start=window_start,
        window_end=window_end,
        region_ids=regions,
    )
    regions_reporting = _regions_reporting_on_date(
        session,
        commodity_id=commodity_id,
        as_of_date=latest_as_of,
        region_ids=regions,
    ) if latest_as_of else 0
    days_with_data = _distinct_weather_days(
        session,
        commodity_id=commodity_id,
        window_start=window_start,
        window_end=window_end,
        region_ids=regions,
    )
    latest_observed = _max_weather_observed_at(
        session,
        commodity_id=commodity_id,
        window_start=window_start,
        window_end=window_end,
        region_ids=regions,
    )
    anomaly_count = _count_weather_anomalies(
        session,
        commodity_id=commodity_id,
        window_start=window_start,
        window_end=window_end,
        region_ids=regions,
    )
    cov = coverage_ratio(regions_reporting, len(regions))
    comp = completeness_ratio(days_with_data, window_days)
    lag = lag_hours(latest_observed, now=now)

    return WeatherQualityMetrics(
        regions_expected=len(regions),
        regions_reporting=regions_reporting,
        coverage_ratio=cov,
        window_days=window_days,
        days_with_data=days_with_data,
        completeness_ratio=comp,
        latest_as_of_date=latest_as_of,
        latest_observed_at=latest_observed,
        weather_lag_hours=lag,
        anomaly_count=anomaly_count,
    )


def _build_source_health(
    *,
    ag_metrics: AgmarknetQualityMetrics,
    weather_metrics: WeatherQualityMetrics | None,
) -> dict:
    ag_health = classify_source_health(
        coverage_ratio=ag_metrics.coverage_ratio,
        completeness_ratio=ag_metrics.completeness_ratio,
        lag_hours_value=ag_metrics.agmarknet_lag_hours,
        has_data=ag_metrics.markets_reporting > 0,
    )
    payload: dict = {
        "agmarknet": ag_health,
        "agmarknet_detail": ag_metrics.to_source_health_detail(),
    }
    if weather_metrics is not None:
        weather_health = classify_source_health(
            coverage_ratio=weather_metrics.coverage_ratio,
            completeness_ratio=weather_metrics.completeness_ratio,
            lag_hours_value=weather_metrics.weather_lag_hours,
            has_data=weather_metrics.regions_reporting > 0,
        )
        payload["weather"] = weather_health
        payload["weather_detail"] = weather_metrics.to_source_health_detail()
    return payload


def _combined_overall_score(
    *,
    ag_metrics: AgmarknetQualityMetrics,
    weather_metrics: WeatherQualityMetrics | None,
) -> Decimal:
    price_rows = ag_metrics.days_with_data * max(ag_metrics.markets_reporting, 1)
    ag_score = compute_overall_quality_score(
        coverage_ratio=ag_metrics.coverage_ratio,
        completeness_ratio=ag_metrics.completeness_ratio,
        lag_hours_value=ag_metrics.agmarknet_lag_hours,
        anomaly_count=ag_metrics.anomaly_count,
        row_count=max(price_rows, 1),
    )
    if weather_metrics is None or weather_metrics.regions_reporting <= 0:
        return ag_score
    weather_rows = weather_metrics.days_with_data * max(
        weather_metrics.regions_reporting, 1
    )
    weather_score = compute_overall_quality_score(
        coverage_ratio=weather_metrics.coverage_ratio,
        completeness_ratio=weather_metrics.completeness_ratio,
        lag_hours_value=weather_metrics.weather_lag_hours,
        anomaly_count=weather_metrics.anomaly_count,
        row_count=max(weather_rows, 1),
    )
    combined = (float(ag_score) + float(weather_score)) / 2.0
    return Decimal(str(round(combined, 4)))


def _max_as_of_date(
    session: Session,
    *,
    window_start: date,
    window_end: date,
    market_ids: tuple[str, ...],
) -> date | None:
    stmt = select(func.max(PriceObservationModel.as_of_date)).where(
        PriceObservationModel.source == SOURCE_AGMARKNET,
        PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
        PriceObservationModel.market_id.in_(market_ids),
        PriceObservationModel.as_of_date >= window_start,
        PriceObservationModel.as_of_date <= window_end,
    )
    return session.scalar(stmt)


def _markets_reporting_on_date(
    session: Session,
    *,
    as_of_date: date,
    market_ids: tuple[str, ...],
) -> int:
    stmt = select(func.count(func.distinct(PriceObservationModel.market_id))).where(
        PriceObservationModel.source == SOURCE_AGMARKNET,
        PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
        PriceObservationModel.market_id.in_(market_ids),
        PriceObservationModel.as_of_date == as_of_date,
    )
    return int(session.scalar(stmt) or 0)


def _distinct_days_with_price_data(
    session: Session,
    *,
    window_start: date,
    window_end: date,
    market_ids: tuple[str, ...],
) -> int:
    stmt = select(func.count(func.distinct(PriceObservationModel.as_of_date))).where(
        PriceObservationModel.source == SOURCE_AGMARKNET,
        PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
        PriceObservationModel.market_id.in_(market_ids),
        PriceObservationModel.as_of_date >= window_start,
        PriceObservationModel.as_of_date <= window_end,
    )
    return int(session.scalar(stmt) or 0)


def _max_observed_at(
    session: Session,
    *,
    window_start: date,
    window_end: date,
    market_ids: tuple[str, ...],
) -> datetime | None:
    stmt = select(func.max(PriceObservationModel.observed_at)).where(
        PriceObservationModel.source == SOURCE_AGMARKNET,
        PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
        PriceObservationModel.market_id.in_(market_ids),
        PriceObservationModel.as_of_date >= window_start,
        PriceObservationModel.as_of_date <= window_end,
    )
    return session.scalar(stmt)


def _count_anomalies(
    session: Session,
    *,
    window_start: date,
    window_end: date,
    market_ids: tuple[str, ...],
) -> int:
    price_stmt = (
        select(func.count())
        .select_from(PriceObservationModel)
        .where(
            PriceObservationModel.source == SOURCE_AGMARKNET,
            PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
            PriceObservationModel.market_id.in_(market_ids),
            PriceObservationModel.as_of_date >= window_start,
            PriceObservationModel.as_of_date <= window_end,
            PriceObservationModel.validation_status.notin_(VALID_VALIDATION_STATUSES),
        )
    )
    arrival_stmt = (
        select(func.count())
        .select_from(ArrivalObservationModel)
        .where(
            ArrivalObservationModel.source == SOURCE_AGMARKNET,
            ArrivalObservationModel.commodity_id == COTTON_COMMODITY_ID,
            ArrivalObservationModel.market_id.in_(market_ids),
            ArrivalObservationModel.as_of_date >= window_start,
            ArrivalObservationModel.as_of_date <= window_end,
            ArrivalObservationModel.validation_status.notin_(
                VALID_VALIDATION_STATUSES
            ),
        )
    )
    return int(session.scalar(price_stmt) or 0) + int(
        session.scalar(arrival_stmt) or 0
    )


def _max_weather_as_of_date(
    session: Session,
    *,
    commodity_id: str,
    window_start: date,
    window_end: date,
    region_ids: tuple[str, ...],
) -> date | None:
    stmt = select(func.max(WeatherObservationModel.as_of_date)).where(
        WeatherObservationModel.source == WEATHER_SOURCE_NASA_POWER,
        WeatherObservationModel.commodity_id == commodity_id,
        WeatherObservationModel.region_id.in_(region_ids),
        WeatherObservationModel.as_of_date >= window_start,
        WeatherObservationModel.as_of_date <= window_end,
    )
    return session.scalar(stmt)


def _regions_reporting_on_date(
    session: Session,
    *,
    commodity_id: str,
    as_of_date: date,
    region_ids: tuple[str, ...],
) -> int:
    stmt = select(func.count(func.distinct(WeatherObservationModel.region_id))).where(
        WeatherObservationModel.source == WEATHER_SOURCE_NASA_POWER,
        WeatherObservationModel.commodity_id == commodity_id,
        WeatherObservationModel.region_id.in_(region_ids),
        WeatherObservationModel.as_of_date == as_of_date,
    )
    return int(session.scalar(stmt) or 0)


def _distinct_weather_days(
    session: Session,
    *,
    commodity_id: str,
    window_start: date,
    window_end: date,
    region_ids: tuple[str, ...],
) -> int:
    stmt = select(func.count(func.distinct(WeatherObservationModel.as_of_date))).where(
        WeatherObservationModel.source == WEATHER_SOURCE_NASA_POWER,
        WeatherObservationModel.commodity_id == commodity_id,
        WeatherObservationModel.region_id.in_(region_ids),
        WeatherObservationModel.as_of_date >= window_start,
        WeatherObservationModel.as_of_date <= window_end,
    )
    return int(session.scalar(stmt) or 0)


def _max_weather_observed_at(
    session: Session,
    *,
    commodity_id: str,
    window_start: date,
    window_end: date,
    region_ids: tuple[str, ...],
) -> datetime | None:
    stmt = select(func.max(WeatherObservationModel.observed_at)).where(
        WeatherObservationModel.source == WEATHER_SOURCE_NASA_POWER,
        WeatherObservationModel.commodity_id == commodity_id,
        WeatherObservationModel.region_id.in_(region_ids),
        WeatherObservationModel.as_of_date >= window_start,
        WeatherObservationModel.as_of_date <= window_end,
    )
    return session.scalar(stmt)


def _count_weather_anomalies(
    session: Session,
    *,
    commodity_id: str,
    window_start: date,
    window_end: date,
    region_ids: tuple[str, ...],
) -> int:
    stmt = (
        select(func.count())
        .select_from(WeatherObservationModel)
        .where(
            WeatherObservationModel.source == WEATHER_SOURCE_NASA_POWER,
            WeatherObservationModel.commodity_id == commodity_id,
            WeatherObservationModel.region_id.in_(region_ids),
            WeatherObservationModel.as_of_date >= window_start,
            WeatherObservationModel.as_of_date <= window_end,
            WeatherObservationModel.validation_status.notin_(VALID_VALIDATION_STATUSES),
        )
    )
    return int(session.scalar(stmt) or 0)


def render_data_quality_report_markdown(
    *,
    result: QualitySnapshotResult,
    ag_metrics: AgmarknetQualityMetrics,
    weather_metrics: WeatherQualityMetrics | None = None,
) -> str:
    """Render PI6 Track E report body for docs/reviews/DATA_QUALITY_REPORT.md."""
    lines = [
        "# Data Quality Snapshot Report — PI6 Track E",
        "",
        "**Date:** 2026-06-04",
        "**PI:** PI6 Track E (KDO — `data_quality_snapshot` ingest wiring)",
        "**Status:** Snapshot writer wired to Agmarknet + optional weather ingest",
        "",
        "---",
        "",
        "## 1. Verdict",
        "",
        "| Question | Answer |",
        "|----------|--------|",
        f"| Snapshot persisted? | **Yes** — `quality_snapshot_id` `{result.quality_snapshot_id}` |",
        f"| Active `registry_id` (FK) | `{result.registry_id}` |",
        f"| `as_of_date` | `{result.as_of_date.isoformat()}` |",
        f"| `overall_quality_score` | **{result.overall_quality_score}** |",
        f"| `agmarknet_lag_hours` | **{result.agmarknet_lag_hours}** |",
        "",
        "---",
        "",
        "## 2. Agmarknet metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Markets reporting / expected | **{ag_metrics.markets_reporting}** / "
        f"**{ag_metrics.markets_expected}** |",
        f"| Coverage ratio | **{ag_metrics.coverage_ratio:.4f}** |",
        f"| Days with data / window | **{ag_metrics.days_with_data}** / "
        f"**{ag_metrics.window_days}** |",
        f"| Completeness ratio | **{ag_metrics.completeness_ratio:.4f}** |",
        f"| Latest `as_of_date` | `{ag_metrics.latest_as_of_date}` |",
        f"| Anomaly count (non-validated) | **{ag_metrics.anomaly_count}** |",
        f"| Source health | `{result.source_health.get('agmarknet')}` |",
        "",
    ]
    if weather_metrics is not None:
        lines.extend(
            [
                "## 3. Weather metrics (NASA POWER)",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Regions reporting / expected | **{weather_metrics.regions_reporting}** / "
                f"**{weather_metrics.regions_expected}** |",
                f"| Coverage ratio | **{weather_metrics.coverage_ratio:.4f}** |",
                f"| Days with data / window | **{weather_metrics.days_with_data}** / "
                f"**{weather_metrics.window_days}** |",
                f"| Completeness ratio | **{weather_metrics.completeness_ratio:.4f}** |",
                f"| Source health | `{result.source_health.get('weather')}` |",
                "",
            ]
        )
    lines.extend(
        [
            "---",
            "",
            "## 4. Deliverables",
            "",
            "| Artifact | Path |",
            "|----------|------|",
            "| Quality service | `backend/app/services/quality/snapshot_service.py` |",
            "| Metrics helpers | `backend/app/services/quality/metrics.py` |",
            "| Repository upsert | `backend/app/persistence/repositories/quality.py` |",
            "| Unit tests | `tests/unit/test_data_quality_ingest.py` |",
            "",
            "---",
            "",
            "## 5. Sample `source_health` fields",
            "",
            "```json",
        ]
    )
    import json

    lines.append(json.dumps(result.source_health, indent=2))
    lines.extend(["```", ""])
    return "\n".join(lines)


__all__ = [
    "DataQualitySnapshotService",
    "QualitySnapshotResult",
    "compute_agmarknet_metrics",
    "compute_weather_metrics",
    "render_data_quality_report_markdown",
]
