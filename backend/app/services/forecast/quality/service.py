"""ForecastQualityService — PI11 Track D backtest KPIs (MAE, RMSE, MAPE, Coverage)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.persistence.models.forecast_quality import ForecastQualityMetricModel
from backend.app.persistence.repositories.forecast_quality import (
    ForecastQualityMetricRepository,
)
from backend.app.services.forecast.quality.metrics import (
    DEFAULT_HORIZONS,
    ForecastEvaluationPair,
    HorizonQualityMetrics,
    build_forecast_quality_by_horizon,
)


@dataclass(frozen=True, slots=True)
class ForecastQualityResult:
    """Outcome of a forecast quality assessment."""

    commodity_id: str
    as_of_date: date
    registry_id: UUID
    model_version: str | None
    assessment_source: str
    by_horizon: dict[int, HorizonQualityMetrics]
    sample_count_total: int

    def to_report_detail(self) -> dict[str, object]:
        return {
            "commodity_id": self.commodity_id,
            "as_of_date": self.as_of_date.isoformat(),
            "registry_id": str(self.registry_id),
            "model_version": self.model_version,
            "assessment_source": self.assessment_source,
            "sample_count_total": self.sample_count_total,
            "by_horizon": {
                str(horizon): metrics.to_detail()
                for horizon, metrics in sorted(self.by_horizon.items())
            },
        }


class ForecastQualityService:
    """Compute and persist forecast backtest KPIs — no user-facing API."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = ForecastQualityMetricRepository(session)

    def assess(
        self,
        pairs: list[ForecastEvaluationPair],
        *,
        commodity_id: str,
        as_of_date: date,
        registry_id: UUID,
        model_version: str | None = None,
        assessment_source: str = "backtest",
        horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    ) -> ForecastQualityResult:
        """Compute MAE, RMSE, MAPE, and interval coverage per horizon."""
        by_horizon = build_forecast_quality_by_horizon(pairs, horizons=horizons)
        total = sum(metrics.sample_count for metrics in by_horizon.values())
        return ForecastQualityResult(
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry_id,
            model_version=model_version,
            assessment_source=assessment_source,
            by_horizon=by_horizon,
            sample_count_total=total,
        )

    def persist(
        self,
        result: ForecastQualityResult,
        *,
        forecast_version_id: UUID | None = None,
    ) -> list[ForecastQualityMetricModel]:
        """Upsert one persisted row per horizon with non-zero sample count."""
        persisted: list[ForecastQualityMetricModel] = []
        for horizon_days, metrics in sorted(result.by_horizon.items()):
            if metrics.sample_count == 0:
                continue
            entity = ForecastQualityMetricModel(
                commodity_id=result.commodity_id,
                as_of_date=result.as_of_date,
                registry_id=result.registry_id,
                horizon_days=horizon_days,
                model_version=result.model_version,
                forecast_version_id=forecast_version_id,
                assessment_source=result.assessment_source,
                sample_count=metrics.sample_count,
                mae=metrics.mae,
                rmse=metrics.rmse,
                mape=metrics.mape,
                coverage=metrics.coverage,
                metrics_detail=metrics.to_detail(),
            )
            persisted.append(self._repo.upsert_metric(entity))
        return persisted

    def assess_and_persist(
        self,
        pairs: list[ForecastEvaluationPair],
        *,
        commodity_id: str,
        as_of_date: date,
        registry_id: UUID,
        model_version: str | None = None,
        assessment_source: str = "backtest",
        forecast_version_id: UUID | None = None,
        horizons: tuple[int, ...] = DEFAULT_HORIZONS,
    ) -> tuple[ForecastQualityResult, list[ForecastQualityMetricModel]]:
        """Compute KPIs and write ``forecast_quality_metric`` rows."""
        result = self.assess(
            pairs,
            commodity_id=commodity_id,
            as_of_date=as_of_date,
            registry_id=registry_id,
            model_version=model_version,
            assessment_source=assessment_source,
            horizons=horizons,
        )
        rows = self.persist(result, forecast_version_id=forecast_version_id)
        return result, rows

    def persist_precomputed(
        self,
        result: ForecastQualityResult,
        *,
        forecast_version_id: UUID | None = None,
    ) -> list[ForecastQualityMetricModel]:
        """Persist a pre-built result (e.g. Track A rolling OOS aggregates)."""
        return self.persist(result, forecast_version_id=forecast_version_id)


def render_forecast_quality_report_markdown(
    *,
    result: ForecastQualityResult,
    persistence_table: str = "forecast_quality_metric",
) -> str:
    """Render PI11 Track D report body for docs/reviews/FORECAST_QUALITY_REPORT.md."""
    lines = [
        "# Forecast Quality Report — PI11 Track D",
        "",
        "**Date:** 2026-06-04",
        "**PI:** PI11 Track D (KDO — `ForecastQualityService`)",
        "**Status:** Backtest KPIs from evaluation pairs (no user-facing forecast API)",
        "",
        "---",
        "",
        "## 1. Verdict",
        "",
        "| Question | Answer |",
        "|----------|--------|",
        f"| Commodity / `as_of_date` | `{result.commodity_id}` / `{result.as_of_date.isoformat()}` |",
        f"| Active `registry_id` (FK) | `{result.registry_id}` |",
        f"| `model_version` | `{result.model_version}` |",
        f"| Assessment source | `{result.assessment_source}` |",
        f"| Total evaluation pairs | **{result.sample_count_total}** |",
        "| Forecast quality service operational? | **Yes** |",
        "",
        "---",
        "",
        "## 2. KPIs by horizon (TDS-000)",
        "",
        "| Horizon (days) | n | MAE | RMSE | MAPE (%) | Coverage |",
        "|----------------|---|-----|------|----------|----------|",
    ]
    for horizon_days in sorted(result.by_horizon):
        metrics = result.by_horizon[horizon_days]
        lines.append(
            f"| **{horizon_days}** | **{metrics.sample_count}** | "
            f"{_fmt(metrics.mae)} | {_fmt(metrics.rmse)} | "
            f"{_fmt(metrics.mape)} | {_fmt(metrics.coverage)} |"
        )
    lines.extend(
        [
            "",
            "Coverage = fraction of realized prices inside `[band_low, band_high]` "
            "(TDS-011 §5.1 interval reliability). MAPE excludes near-zero actuals.",
            "",
            "---",
            "",
            "## 3. Deliverables",
            "",
            "| Artifact | Path |",
            "|----------|------|",
            "| Forecast quality service | `backend/app/services/forecast/quality/service.py` |",
            "| Metrics helpers | `backend/app/services/forecast/quality/metrics.py` |",
            f"| Persistence table | `{persistence_table}` |",
            "| Migration | `backend/app/persistence/migrations/versions/0015_forecast_quality_metric.py` |",
            "| Unit tests | `tests/unit/test_forecast_quality.py` |",
            "",
            "---",
            "",
            "## 4. Sample metrics payload",
            "",
            "```json",
        ]
    )
    import json

    lines.append(json.dumps(result.to_report_detail(), indent=2))
    lines.extend(["```", ""])
    return "\n".join(lines)


def _fmt(value: float | None) -> str:
    if value is None:
        return "—"
    return f"**{value:.4f}**"


__all__ = [
    "ForecastQualityResult",
    "ForecastQualityService",
    "render_forecast_quality_report_markdown",
]
