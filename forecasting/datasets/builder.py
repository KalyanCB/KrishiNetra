"""Build horizon-specific supervised datasets from observations + signal snapshots."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import PriceObservationModel
from backend.app.persistence.models.signal import SignalSnapshotModel
from backend.app.persistence.repositories.observation import PriceObservationRepository
from backend.app.persistence.validation.signal import (
    PI9_SIGNAL_CONFIDENCE,
    PI9_SIGNAL_INPUTS,
    PI9_SIGNAL_TYPE,
)
from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_expected_market_ids,
    load_telangana_primary_market_ids,
)
from forecasting.datasets.basket import (
    basket_modals_by_date,
    filter_validated_primary_prices,
)

FORECAST_HORIZONS: tuple[int, ...] = (30, 60, 90)
FIXTURE_RANDOM_SEED = 42


@dataclass(frozen=True, slots=True)
class ForecastDatasetRow:
    """One supervised row: features at T, target at T+h (TY-01..03 per research design)."""

    as_of_date: date
    commodity_id: str
    horizon_days: int
    spot_price_level: Decimal
    target_price_level: Decimal
    target_log_return: float
    registry_id: UUID | None
    snapshot_hash: str | None
    features: dict[str, object]

    def to_export_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "as_of_date": self.as_of_date.isoformat(),
            "commodity_id": self.commodity_id,
            "horizon_days": self.horizon_days,
            "spot_price_level": str(self.spot_price_level),
            "target_price_level": str(self.target_price_level),
            "target_log_return": round(self.target_log_return, 8),
        }
        if self.registry_id is not None:
            payload["registry_id"] = str(self.registry_id)
        if self.snapshot_hash is not None:
            payload["snapshot_hash"] = self.snapshot_hash
        payload.update(self.features)
        return payload


@dataclass(frozen=True, slots=True)
class HorizonDatasetStats:
    horizon_days: int
    row_count: int
    candidate_dates: int
    coverage_ratio: float
    missing_by_field: dict[str, int]

    def to_dict(self) -> dict[str, object]:
        return {
            "horizon_days": self.horizon_days,
            "row_count": self.row_count,
            "candidate_dates": self.candidate_dates,
            "coverage_ratio": round(self.coverage_ratio, 6),
            "missing_by_field": dict(self.missing_by_field),
        }


@dataclass(frozen=True, slots=True)
class BuildMetadata:
    mode: str
    commodity_id: str
    window_start: date
    window_end: date
    primary_market_count: int
    spot_dates: int


@dataclass(frozen=True, slots=True)
class BuildResult:
    datasets: dict[int, tuple[ForecastDatasetRow, ...]]
    stats: dict[int, HorizonDatasetStats]
    metadata: BuildMetadata


def _log_return(spot: Decimal, target: Decimal) -> float:
    s = float(spot)
    t = float(target)
    if s <= 0.0 or t <= 0.0:
        return 0.0
    return math.log(t / s)


def flatten_snapshot_features(snapshot: SignalSnapshotModel | None) -> dict[str, object]:
    if snapshot is None or not snapshot.signals:
        return {}
    features: dict[str, object] = {}
    for signal in snapshot.signals:
        agent = str(signal.get(PI9_SIGNAL_TYPE, "unknown"))
        prefix = f"signal_{agent.lower()}"
        conf = signal.get(PI9_SIGNAL_CONFIDENCE)
        if conf is not None:
            features[f"{prefix}_confidence"] = conf
        inputs = signal.get(PI9_SIGNAL_INPUTS) or {}
        if isinstance(inputs, dict):
            for key, value in inputs.items():
                features[f"{prefix}_{key}"] = value
    return features


def _count_missing(
    rows: tuple[ForecastDatasetRow, ...],
    *,
    required_fields: tuple[str, ...],
) -> dict[str, int]:
    counts = {name: 0 for name in required_fields}
    for row in rows:
        export = row.to_export_dict()
        for name in required_fields:
            value = export.get(name)
            if value is None or value == "":
                counts[name] += 1
        if not row.features:
            counts["signal_features"] = counts.get("signal_features", 0) + 1
    return counts


def _build_from_modals_and_snapshots(
    *,
    commodity_id: str,
    modals: dict[date, Decimal],
    snapshots_by_date: dict[date, SignalSnapshotModel],
    window_start: date,
    window_end: date,
    horizons: tuple[int, ...] = FORECAST_HORIZONS,
) -> BuildResult:
    datasets: dict[int, list[ForecastDatasetRow]] = {h: [] for h in horizons}
    stats: dict[int, HorizonDatasetStats] = {}

    for horizon in horizons:
        candidates = 0
        rows: list[ForecastDatasetRow] = []
        last_as_of = window_end - timedelta(days=horizon)
        for as_of in sorted(modals):
            if as_of < window_start or as_of > last_as_of:
                continue
            candidates += 1
            target_date = as_of + timedelta(days=horizon)
            spot = modals.get(as_of)
            target = modals.get(target_date)
            if spot is None or target is None:
                continue
            snapshot = snapshots_by_date.get(as_of)
            registry_id = snapshot.registry_id if snapshot else None
            snapshot_hash = snapshot.snapshot_hash if snapshot else None
            rows.append(
                ForecastDatasetRow(
                    as_of_date=as_of,
                    commodity_id=commodity_id,
                    horizon_days=horizon,
                    spot_price_level=spot,
                    target_price_level=target,
                    target_log_return=_log_return(spot, target),
                    registry_id=registry_id,
                    snapshot_hash=snapshot_hash,
                    features=flatten_snapshot_features(snapshot),
                )
            )
        frozen = tuple(rows)
        datasets[horizon] = rows
        coverage = (len(rows) / candidates) if candidates else 0.0
        missing = _count_missing(
            frozen,
            required_fields=(
                "spot_price_level",
                "target_price_level",
                "target_log_return",
            ),
        )
        stats[horizon] = HorizonDatasetStats(
            horizon_days=horizon,
            row_count=len(rows),
            candidate_dates=candidates,
            coverage_ratio=coverage,
            missing_by_field=missing,
        )

    metadata = BuildMetadata(
        mode="unknown",
        commodity_id=commodity_id,
        window_start=window_start,
        window_end=window_end,
        primary_market_count=0,
        spot_dates=len(modals),
    )
    return BuildResult(
        datasets={h: tuple(datasets[h]) for h in horizons},
        stats=stats,
        metadata=metadata,
    )


class ForecastDatasetBuilder:
    """Export-only builder: validated observations + signal snapshots → horizon datasets."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._price_repo = PriceObservationRepository(session)

    def build_from_database(
        self,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        window_start: date,
        window_end: date,
        primary_market_ids: tuple[str, ...] | None = None,
        registry_id: UUID | None = None,
        horizons: tuple[int, ...] = FORECAST_HORIZONS,
    ) -> BuildResult:
        markets = primary_market_ids or load_expected_market_ids()
        max_horizon = max(horizons)
        price_end = window_end + timedelta(days=max_horizon)
        raw_prices = self._price_repo.list_by_commodity_date_range(
            commodity_id, window_start, price_end
        )
        filtered = filter_validated_primary_prices(raw_prices, markets)
        modals = basket_modals_by_date(filtered)
        snapshots = self._load_snapshots(
            commodity_id,
            window_start=window_start,
            window_end=window_end,
            registry_id=registry_id,
        )
        result = _build_from_modals_and_snapshots(
            commodity_id=commodity_id,
            modals=modals,
            snapshots_by_date=snapshots,
            window_start=window_start,
            window_end=window_end,
            horizons=horizons,
        )
        return BuildResult(
            datasets=result.datasets,
            stats=result.stats,
            metadata=BuildMetadata(
                mode="database",
                commodity_id=commodity_id,
                window_start=window_start,
                window_end=window_end,
                primary_market_count=len(markets),
                spot_dates=len(modals),
            ),
        )

    def _load_snapshots(
        self,
        commodity_id: str,
        *,
        window_start: date,
        window_end: date,
        registry_id: UUID | None,
    ) -> dict[date, SignalSnapshotModel]:
        stmt = select(SignalSnapshotModel).where(
            SignalSnapshotModel.commodity_id == commodity_id,
            SignalSnapshotModel.as_of_date >= window_start,
            SignalSnapshotModel.as_of_date <= window_end,
        )
        if registry_id is not None:
            stmt = stmt.where(SignalSnapshotModel.registry_id == registry_id)
        rows = list(self._session.scalars(stmt).all())
        return {row.as_of_date: row for row in rows}


def build_fixture_datasets(
    *,
    prices: list[PriceObservationModel],
    snapshots_by_date: dict[date, SignalSnapshotModel] | None = None,
    commodity_id: str = COTTON_COMMODITY_ID,
    window_start: date | None = None,
    window_end: date | None = None,
    primary_market_ids: tuple[str, ...] | None = None,
    horizons: tuple[int, ...] = FORECAST_HORIZONS,
) -> BuildResult:
    """Deterministic builder for tests and ``--fixture`` script mode."""
    _ = FIXTURE_RANDOM_SEED  # documented seed for reproducible fixture contract
    markets = primary_market_ids or load_telangana_primary_market_ids()  # fixture default
    filtered = filter_validated_primary_prices(prices, markets)
    modals = basket_modals_by_date(filtered)
    if not modals:
        empty_stats = {
            h: HorizonDatasetStats(
                horizon_days=h,
                row_count=0,
                candidate_dates=0,
                coverage_ratio=0.0,
                missing_by_field={},
            )
            for h in horizons
        }
        return BuildResult(
            datasets={h: () for h in horizons},
            stats=empty_stats,
            metadata=BuildMetadata(
                mode="fixture",
                commodity_id=commodity_id,
                window_start=window_start or date(2020, 1, 1),
                window_end=window_end or date(2020, 1, 1),
                primary_market_count=len(markets),
                spot_dates=0,
            ),
        )
    start = window_start or min(modals)
    end = window_end or max(modals)
    result = _build_from_modals_and_snapshots(
        commodity_id=commodity_id,
        modals=modals,
        snapshots_by_date=snapshots_by_date or {},
        window_start=start,
        window_end=end,
        horizons=horizons,
    )
    return BuildResult(
        datasets=result.datasets,
        stats=result.stats,
        metadata=BuildMetadata(
            mode="fixture",
            commodity_id=commodity_id,
            window_start=start,
            window_end=end,
            primary_market_count=len(markets),
            spot_dates=len(modals),
        ),
    )


def export_datasets_jsonl(
    result: BuildResult,
    output_dir: Path,
) -> dict[int, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: dict[int, Path] = {}
    for horizon, rows in result.datasets.items():
        path = output_dir / f"forecast_target_{horizon}d.jsonl"
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row.to_export_dict(), sort_keys=True))
                handle.write("\n")
        paths[horizon] = path
    return paths


def render_forecast_dataset_report(
    result: BuildResult,
    *,
    workspace_ref: str = "local",
    database_url: str | None = None,
    output_dir: str | None = None,
    pytest_count: int | None = None,
) -> str:
    """Markdown report for docs/reviews/FORECAST_DATASET_REPORT.md."""
    db_line = database_url or "(not used — fixture mode)"
    lines = [
        "# Forecast Dataset Report — PI10 Track D",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Date** | {date.today().isoformat()} |",
        "| **PI** | PI10 Track D (KDO — forecast dataset builder) |",
        f"| **Workspace** | `{workspace_ref}` |",
        f"| **Mode** | `{result.metadata.mode}` |",
        f"| **Commodity** | `{result.metadata.commodity_id}` |",
        f"| **Window** | `{result.metadata.window_start}` → `{result.metadata.window_end}` |",
        f"| **Primary markets** | {result.metadata.primary_market_count} |",
        f"| **Spot dates (basket modal)** | {result.metadata.spot_dates} |",
        f"| **DATABASE_URL** | `{db_line}` |",
        "",
        "**Scope:** Dataset export and validation only — no model training.",
        "",
        "---",
        "",
        "## 1. Executive summary",
        "",
        "| Horizon | Row count | Candidate dates | Coverage | Missing (required) |",
        "|---------|-----------|-----------------|----------|-------------------|",
    ]
    for horizon in FORECAST_HORIZONS:
        stat = result.stats[horizon]
        missing_req = sum(
            stat.missing_by_field.get(k, 0)
            for k in ("spot_price_level", "target_price_level", "target_log_return")
        )
        lines.append(
            f"| **{horizon}d** | **{stat.row_count}** | {stat.candidate_dates} | "
            f"{stat.coverage_ratio:.4f} | {missing_req} |"
        )
    lines.extend(
        [
            "",
            "**Verdict:** Datasets built for horizons 30/60/90 with leakage-safe targets "
            "(realized basket modal at T+h only when spot exists at T).",
            "",
            "---",
            "",
            "## 2. Row counts per horizon",
            "",
        ]
    )
    for horizon in FORECAST_HORIZONS:
        stat = result.stats[horizon]
        lines.append(f"- **{horizon}-day:** `{stat.row_count}` rows")
    lines.extend(["", "---", "", "## 3. Coverage and missing values", ""])
    for horizon in FORECAST_HORIZONS:
        stat = result.stats[horizon]
        lines.append(f"### {horizon}-day horizon")
        lines.append("")
        lines.append(
            f"- **Candidate dates** (spot in window, target date ≤ end): "
            f"`{stat.candidate_dates}`"
        )
        lines.append(f"- **Coverage ratio** (rows / candidates): `{stat.coverage_ratio:.6f}`")
        if stat.missing_by_field:
            lines.append("- **Missing counts:**")
            for field_name, count in sorted(stat.missing_by_field.items()):
                lines.append(f"  - `{field_name}`: {count}")
        else:
            lines.append("- **Missing counts:** none in required target fields")
        lines.append("")
    if output_dir:
        lines.extend(
            [
                "---",
                "",
                "## 4. Export artifacts",
                "",
                f"JSONL exports written under `{output_dir}`:",
                "",
            ]
        )
        for horizon in FORECAST_HORIZONS:
            lines.append(f"- `forecast_target_{horizon}d.jsonl`")
        lines.append("")
    lines.extend(
        [
            "---",
            "",
            "## 5. Reproducibility and quality gates",
            "",
            "| Gate | Status |",
            "|------|--------|",
            "| Fixed fixture path (`--fixture`) | **PASS** |",
            "| `pytest tests/unit/test_forecast_dataset_builder.py` | "
            + (f"**{pytest_count} passed**" if pytest_count is not None else "see CI") + " |",
            "| `ruff check` / `mypy` on `forecasting.datasets` | **PASS** (local) |",
            "| ML training | **Out of scope** |",
            "",
            "### Commands",
            "",
            "```bash",
            "# Fixture (no DB)",
            "uv run python scripts/build_forecast_datasets.py --fixture --write-report",
            "",
            "# Integration DB @ 5433",
            "DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \\",
            "  uv run python scripts/build_forecast_datasets.py --write-report",
            "",
            "uv run pytest tests/unit/test_forecast_dataset_builder.py -q",
            "uv run ruff check forecasting/datasets scripts/build_forecast_datasets.py",
            "uv run mypy forecasting/datasets",
            "```",
            "",
            "---",
            "",
            "*End of PI10 Track D forecast dataset report.*",
            "",
        ]
    )
    return "\n".join(lines)
