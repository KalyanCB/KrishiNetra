"""PI11 Track C — Random Forest feature importance from baseline model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import numpy as np

from backend.app.services.forecast.features.assembler import assemble_forecast_features
from forecasting.datasets.builder import (
    FORECAST_HORIZONS,
    ForecastDatasetBuilder,
    build_fixture_datasets,
)
from forecasting.datasets.fixtures import (
    fixture_price_window,
    fixture_primary_markets,
    fixture_snapshots_by_date,
)
from forecasting.features.fixtures import (
    fixture_futures_signal,
    fixture_market_signal,
    fixture_weather_signal,
)
from forecasting.features.lineage import (
    group_aggregate_scores,
    group_importances,
    prefixes_from_lineage,
    top_features_per_group,
)
from forecasting.models.baseline_rf import (
    feature_importance_map,
    fit_random_forest_baseline,
    load_track_a_random_forest,
)
from shared.domain.enums import Direction

_DIRECTION_ENCODING = {
    Direction.BULLISH.value: 1.0,
    Direction.BEARISH.value: -1.0,
    Direction.NEUTRAL.value: 0.0,
}


@dataclass(frozen=True, slots=True)
class ImportancePanelRow:
    as_of_date: date
    feature_values: dict[str, object]
    feature_lineage: dict[str, object]
    target_log_return: float


@dataclass(frozen=True, slots=True)
class FeatureImportanceResult:
    mode: str
    horizon_days: int
    row_count: int
    feature_count: int
    model_source: str
    importances: dict[str, float]
    grouped: dict[str, tuple[tuple[str, float], ...]]
    top_per_group: dict[str, tuple[tuple[str, float], ...]]
    group_totals: dict[str, float]
    window_start: date
    window_end: date
    commodity_id: str

    def to_report_detail(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "horizon_days": self.horizon_days,
            "row_count": self.row_count,
            "feature_count": self.feature_count,
            "model_source": self.model_source,
            "window_start": self.window_start.isoformat(),
            "window_end": self.window_end.isoformat(),
            "commodity_id": self.commodity_id,
            "group_totals": self.group_totals,
            "top_per_group": {
                group: [{"feature": n, "importance": s} for n, s in rows]
                for group, rows in self.top_per_group.items()
            },
        }


def coerce_feature_value(raw: object) -> float:
    """Deterministic numeric coercion for sklearn matrix rows."""
    if raw is None:
        return 0.0
    if isinstance(raw, bool):
        return 1.0 if raw else 0.0
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        if raw in _DIRECTION_ENCODING:
            return _DIRECTION_ENCODING[raw]
        try:
            return float(raw)
        except ValueError:
            return 0.0
    return 0.0


def collect_feature_names(rows: tuple[ImportancePanelRow, ...]) -> tuple[str, ...]:
    names: set[str] = set()
    for row in rows:
        names.update(row.feature_values)
    return tuple(sorted(names))


def build_feature_matrix(
    rows: tuple[ImportancePanelRow, ...],
    feature_names: tuple[str, ...],
) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.zeros((len(rows), len(feature_names)), dtype=np.float64)
    targets = np.zeros(len(rows), dtype=np.float64)
    index = {name: idx for idx, name in enumerate(feature_names)}
    for row_idx, row in enumerate(rows):
        targets[row_idx] = row.target_log_return
        for name, raw in row.feature_values.items():
            col = index.get(name)
            if col is not None:
                matrix[row_idx, col] = coerce_feature_value(raw)
    return matrix, targets


def build_fixture_panel(
    *,
    horizon_days: int = 30,
    window_start: date | None = None,
    window_end: date | None = None,
) -> tuple[ImportancePanelRow, ...]:
    """Assemble namespaced features + leakage-safe targets from PI10 fixtures."""
    if horizon_days not in FORECAST_HORIZONS:
        msg = f"horizon_days must be one of {FORECAST_HORIZONS}"
        raise ValueError(msg)

    build_result = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=window_start,
        window_end=window_end,
        primary_market_ids=fixture_primary_markets(),
    )
    targets_by_date = {
        row.as_of_date: row.target_log_return for row in build_result.datasets[horizon_days]
    }

    panel: list[ImportancePanelRow] = []
    for as_of_date in sorted(targets_by_date):
        market = fixture_market_signal(as_of_date=as_of_date)
        weather = fixture_weather_signal(as_of_date=as_of_date)
        futures = fixture_futures_signal(as_of_date=as_of_date)
        feature_values, feature_lineage = assemble_forecast_features(
            as_of_date=as_of_date,
            market=market,
            weather=weather,
            futures=futures,
            use_futures_stub=False,
        )
        panel.append(
            ImportancePanelRow(
                as_of_date=as_of_date,
                feature_values=feature_values,
                feature_lineage=feature_lineage,
                target_log_return=targets_by_date[as_of_date],
            )
        )
    return tuple(panel)


def run_feature_importance_analysis(
    panel: tuple[ImportancePanelRow, ...],
    *,
    horizon_days: int = 30,
    mode: str = "fixture",
    commodity_id: str = "cotton",
    top_k: int = 10,
) -> FeatureImportanceResult:
    """Fit or load RF baseline and rank importances by lineage group."""
    if not panel:
        empty: dict[str, tuple[tuple[str, float], ...]] = {
            "market": (),
            "weather": (),
            "futures": (),
        }
        return FeatureImportanceResult(
            mode=mode,
            horizon_days=horizon_days,
            row_count=0,
            feature_count=0,
            model_source="untrained",
            importances={},
            grouped=empty,
            top_per_group=empty,
            group_totals={"market": 0.0, "weather": 0.0, "futures": 0.0},
            window_start=date(1970, 1, 1),
            window_end=date(1970, 1, 1),
            commodity_id=commodity_id,
        )

    feature_names = collect_feature_names(panel)
    matrix, targets = build_feature_matrix(panel, feature_names)

    loaded = load_track_a_random_forest(horizon_days)
    if loaded is not None:
        artifact_model, artifact_names = loaded
        if artifact_names == feature_names:
            model = artifact_model
            model_source = "track_a_artifact"
        else:
            model = fit_random_forest_baseline(matrix, targets)
            model_source = "fitted_baseline_feature_mismatch"
    else:
        model = fit_random_forest_baseline(matrix, targets)
        model_source = "fitted_baseline"

    importances = feature_importance_map(model, feature_names)
    sample_lineage = panel[0].feature_lineage
    active = prefixes_from_lineage(sample_lineage)
    grouped = group_importances(importances, active_prefixes=active)
    tops = top_features_per_group(grouped, top_k=top_k)
    totals = group_aggregate_scores(grouped)

    return FeatureImportanceResult(
        mode=mode,
        horizon_days=horizon_days,
        row_count=len(panel),
        feature_count=len(feature_names),
        model_source=model_source,
        importances=importances,
        grouped=grouped,
        top_per_group=tops,
        group_totals=totals,
        window_start=panel[0].as_of_date,
        window_end=panel[-1].as_of_date,
        commodity_id=commodity_id,
    )


def build_database_panel(
    session: Any,
    *,
    commodity_id: str,
    window_start: date,
    window_end: date,
    horizon_days: int = 30,
) -> tuple[ImportancePanelRow, ...]:
    """Build panel from DB datasets + ForecastFeatureSnapshot when available."""
    from backend.app.persistence.repositories.forecast import (
        ForecastFeatureSnapshotRepository,
    )

    build_result = ForecastDatasetBuilder(session).build_from_database(
        commodity_id=commodity_id,
        window_start=window_start,
        window_end=window_end,
    )
    snapshot_repo = ForecastFeatureSnapshotRepository(session)
    panel: list[ImportancePanelRow] = []

    for row in sorted(
        build_result.datasets[horizon_days], key=lambda item: item.as_of_date
    ):
        if row.registry_id is None:
            continue
        snapshot = snapshot_repo.get_snapshot(
            commodity_id, row.as_of_date, row.registry_id
        )
        if snapshot is None:
            market = fixture_market_signal(as_of_date=row.as_of_date)
            weather = fixture_weather_signal(as_of_date=row.as_of_date)
            futures = fixture_futures_signal(as_of_date=row.as_of_date)
            feature_values, feature_lineage = assemble_forecast_features(
                as_of_date=row.as_of_date,
                market=market,
                weather=weather,
                futures=futures,
                use_futures_stub=False,
            )
        else:
            feature_values = dict(snapshot.feature_values)
            feature_lineage = dict(snapshot.feature_lineage)
        panel.append(
            ImportancePanelRow(
                as_of_date=row.as_of_date,
                feature_values=feature_values,
                feature_lineage=feature_lineage,
                target_log_return=row.target_log_return,
            )
        )
    return tuple(panel)
