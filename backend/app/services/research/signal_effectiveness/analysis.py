"""Run signal effectiveness analysis (PI10 Track E)."""

from __future__ import annotations

from dataclasses import dataclass

from backend.app.services.research.signal_effectiveness.metrics import (
    FORWARD_HORIZONS_DAYS,
    TRACKED_SIGNALS,
    CorrelationResult,
    correlate_series,
    pick_best_worst,
)
from backend.app.services.research.signal_effectiveness.panel import (
    DailyPanelRow,
    ObservationPanel,
    build_daily_panel,
    panel_summary,
)


@dataclass(frozen=True, slots=True)
class SignalEffectivenessResult:
    """Full correlation study outcome."""

    data_source: str
    window_start: str
    window_end: str
    primary_market_count: int
    price_observation_count: int
    arrival_observation_count: int
    weather_observation_count: int
    panel_summary: dict[str, int | str | None]
    correlations: tuple[CorrelationResult, ...]
    best_signal: CorrelationResult | None
    worst_signal: CorrelationResult | None
    ranking_horizon_days: int

    def to_report_detail(self) -> dict[str, object]:
        return {
            "data_source": self.data_source,
            "window_start": self.window_start,
            "window_end": self.window_end,
            "primary_market_count": self.primary_market_count,
            "price_observation_count": self.price_observation_count,
            "arrival_observation_count": self.arrival_observation_count,
            "weather_observation_count": self.weather_observation_count,
            "panel_summary": self.panel_summary,
            "ranking_horizon_days": self.ranking_horizon_days,
            "best_signal": _correlation_dict(self.best_signal),
            "worst_signal": _correlation_dict(self.worst_signal),
            "correlations": [_correlation_dict(c) for c in self.correlations],
        }


def _correlation_dict(result: CorrelationResult | None) -> dict[str, object] | None:
    if result is None:
        return None
    return {
        "signal": result.signal,
        "horizon_days": result.horizon_days,
        "pearson_r": result.pearson_r,
        "spearman_rho": result.spearman_rho,
        "sample_size": result.sample_size,
        "mean_signal": result.mean_signal,
        "mean_forward_return": result.mean_forward_return,
    }


def run_signal_effectiveness_analysis(
    panel: ObservationPanel,
    *,
    ranking_horizon_days: int = 30,
) -> SignalEffectivenessResult:
    """Build daily panel and correlate four signals vs forward basket-modal returns."""
    rows = build_daily_panel(panel)
    correlations = _correlate_all(rows)
    best, worst = pick_best_worst(correlations, horizon_days=ranking_horizon_days)
    summary = panel_summary(rows)

    return SignalEffectivenessResult(
        data_source=panel.data_source,
        window_start=panel.window_start.isoformat(),
        window_end=panel.window_end.isoformat(),
        primary_market_count=len(panel.primary_market_ids),
        price_observation_count=len(panel.prices),
        arrival_observation_count=len(panel.arrivals),
        weather_observation_count=len(panel.weather),
        panel_summary=summary,
        correlations=correlations,
        best_signal=best,
        worst_signal=worst,
        ranking_horizon_days=ranking_horizon_days,
    )


def _correlate_all(rows: tuple[DailyPanelRow, ...]) -> tuple[CorrelationResult, ...]:
    results: list[CorrelationResult] = []
    for signal in TRACKED_SIGNALS:
        for horizon in FORWARD_HORIZONS_DAYS:
            signal_values: list[float] = []
            forward_returns: list[float] = []
            for row in rows:
                s_val = row.signal_value(signal)
                f_val = row.forward_return(horizon)
                if s_val is None or f_val is None:
                    continue
                signal_values.append(s_val)
                forward_returns.append(f_val)
            results.append(
                correlate_series(
                    signal=signal,
                    horizon_days=horizon,
                    signal_values=signal_values,
                    forward_returns=forward_returns,
                )
            )
    return tuple(results)
