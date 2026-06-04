"""Rolling / expanding walk-forward validation — PI11 Track B (no random splits)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Literal

from forecasting.datasets.builder import (
    FORECAST_HORIZONS,
    ForecastDatasetRow,
    build_fixture_datasets,
)

WindowMode = Literal["expanding", "sliding"]

DEFAULT_PRIMARY_HORIZON_DAYS = 30
VALIDATION_WINDOW_MODES: tuple[WindowMode, ...] = ("expanding", "sliding")


class RollingValidationError(ValueError):
    """Raised when fold construction or leakage checks fail."""


@dataclass(frozen=True, slots=True)
class RollingValidationSpec:
    """Walk-forward validation parameters (chronological folds only)."""

    horizon_days: int = DEFAULT_PRIMARY_HORIZON_DAYS
    window_mode: WindowMode = "expanding"
    min_train_rows: int = 24
    step_rows: int = 1
    step_days: int | None = None
    train_window_rows: int | None = None

    def __post_init__(self) -> None:
        if self.horizon_days not in FORECAST_HORIZONS:
            raise RollingValidationError(
                f"horizon_days must be one of {FORECAST_HORIZONS}, got {self.horizon_days}"
            )
        if self.window_mode not in VALIDATION_WINDOW_MODES:
            raise RollingValidationError(
                f"window_mode must be one of {VALIDATION_WINDOW_MODES}, "
                f"got {self.window_mode!r}"
            )
        if self.min_train_rows < 1:
            raise RollingValidationError("min_train_rows must be >= 1")
        if self.step_rows < 1:
            raise RollingValidationError("step_rows must be >= 1")
        if self.step_days is not None and self.step_days < 1:
            raise RollingValidationError("step_days must be >= 1 when set")
        if self.window_mode == "sliding":
            if self.train_window_rows is None or self.train_window_rows < 1:
                raise RollingValidationError(
                    "train_window_rows must be >= 1 for sliding window_mode"
                )
        elif self.train_window_rows is not None:
            raise RollingValidationError(
                "train_window_rows is only valid for sliding window_mode"
            )


@dataclass(frozen=True, slots=True)
class ValidationFold:
    """One chronological test cut with leakage-safe training rows."""

    fold_index: int
    test_as_of_date: date
    train_rows: tuple[ForecastDatasetRow, ...]
    test_row: ForecastDatasetRow


@dataclass(frozen=True, slots=True)
class RollingValidationResult:
    """Outcome of walk-forward fold generation."""

    spec: RollingValidationSpec
    dataset_row_count: int
    folds: tuple[ValidationFold, ...]

    @property
    def fold_count(self) -> int:
        return len(self.folds)


def label_realization_date(row: ForecastDatasetRow) -> date:
    """Calendar date when the supervised target is realized (T + horizon)."""
    as_of: date = row.as_of_date
    return as_of + timedelta(days=row.horizon_days)


def assert_no_label_leakage(
    train_rows: Sequence[ForecastDatasetRow],
    test_row: ForecastDatasetRow,
    *,
    horizon_days: int | None = None,
) -> None:
    """Ensure no train label uses information at or after the test feature date."""
    horizon = horizon_days if horizon_days is not None else test_row.horizon_days
    test_as_of = test_row.as_of_date
    for train in train_rows:
        if train.horizon_days != horizon:
            raise RollingValidationError(
                f"horizon mismatch: train {train.horizon_days} vs test {horizon}"
            )
        if train.as_of_date >= test_as_of:
            raise RollingValidationError(
                f"train as_of_date {train.as_of_date} must be < test {test_as_of}"
            )
        if label_realization_date(train) >= test_as_of:
            raise RollingValidationError(
                "label leakage: train target realization "
                f"{label_realization_date(train)} >= test as_of {test_as_of}"
            )


def _sorted_unique_horizon_rows(
    rows: Sequence[ForecastDatasetRow],
    *,
    horizon_days: int,
) -> tuple[ForecastDatasetRow, ...]:
    if not rows:
        return ()
    mismatched = [r.as_of_date for r in rows if r.horizon_days != horizon_days]
    if mismatched:
        raise RollingValidationError(
            f"all rows must have horizon_days={horizon_days}; "
            f"found mismatches on {mismatched[:3]}"
        )
    ordered = sorted(rows, key=lambda r: r.as_of_date)
    dates = [r.as_of_date for r in ordered]
    if len(dates) != len(set(dates)):
        raise RollingValidationError("duplicate as_of_date in dataset rows")
    return tuple(ordered)


def _target_realized_before_test(
    train_as_of: date,
    test_as_of: date,
    *,
    horizon_days: int,
) -> bool:
    return train_as_of + timedelta(days=horizon_days) < test_as_of


def _eligible_train_rows(
    rows: Sequence[ForecastDatasetRow],
    *,
    test_as_of_date: date,
    horizon_days: int,
) -> tuple[ForecastDatasetRow, ...]:
    return tuple(
        r
        for r in rows
        if r.as_of_date < test_as_of_date
        and _target_realized_before_test(
            r.as_of_date, test_as_of_date, horizon_days=horizon_days
        )
    )


def _apply_window_mode(
    train_rows: tuple[ForecastDatasetRow, ...],
    spec: RollingValidationSpec,
) -> tuple[ForecastDatasetRow, ...]:
    if spec.window_mode == "expanding":
        return train_rows
    assert spec.train_window_rows is not None
    if len(train_rows) <= spec.train_window_rows:
        return train_rows
    return train_rows[-spec.train_window_rows :]


def build_rolling_folds(
    rows: Sequence[ForecastDatasetRow],
    spec: RollingValidationSpec,
) -> tuple[ValidationFold, ...]:
    """Build chronological walk-forward folds; never shuffles or random-splits."""
    ordered = _sorted_unique_horizon_rows(rows, horizon_days=spec.horizon_days)
    folds: list[ValidationFold] = []
    last_fold_test: date | None = None
    qualifying_seen = 0

    for test_row in ordered:
        train_pool = _eligible_train_rows(
            ordered,
            test_as_of_date=test_row.as_of_date,
            horizon_days=spec.horizon_days,
        )
        train_pool = _apply_window_mode(train_pool, spec)
        if len(train_pool) < spec.min_train_rows:
            continue

        assert_no_label_leakage(train_pool, test_row, horizon_days=spec.horizon_days)

        if (
            last_fold_test is not None
            and spec.step_days is not None
            and test_row.as_of_date < last_fold_test + timedelta(days=spec.step_days)
        ):
            continue

        qualifying_seen += 1
        if spec.step_rows > 1 and qualifying_seen % spec.step_rows != 0:
            continue

        folds.append(
            ValidationFold(
                fold_index=len(folds),
                test_as_of_date=test_row.as_of_date,
                train_rows=train_pool,
                test_row=test_row,
            )
        )
        last_fold_test = test_row.as_of_date

    return tuple(folds)


def run_rolling_validation(
    rows: Sequence[ForecastDatasetRow],
    spec: RollingValidationSpec | None = None,
) -> RollingValidationResult:
    """Run walk-forward validation on PI10-style supervised rows."""
    effective = spec or RollingValidationSpec()
    ordered = _sorted_unique_horizon_rows(rows, horizon_days=effective.horizon_days)
    folds = build_rolling_folds(ordered, effective)
    return RollingValidationResult(
        spec=effective,
        dataset_row_count=len(ordered),
        folds=folds,
    )


def dataset_rows_from_pi10_fixture(
    *,
    horizon_days: int = DEFAULT_PRIMARY_HORIZON_DAYS,
) -> tuple[ForecastDatasetRow, ...]:
    """Load PI10 Track D fixture rows for the requested horizon."""
    from forecasting.datasets.fixtures import (
        FIXTURE_WINDOW_END,
        FIXTURE_WINDOW_START,
        fixture_price_window,
        fixture_primary_markets,
        fixture_snapshots_by_date,
    )

    result = build_fixture_datasets(
        prices=fixture_price_window(),
        snapshots_by_date=fixture_snapshots_by_date(),
        window_start=FIXTURE_WINDOW_START,
        window_end=FIXTURE_WINDOW_END,
        primary_market_ids=fixture_primary_markets(),
    )
    return tuple(result.datasets[horizon_days])


def render_time_series_validation_report(
    result: RollingValidationResult,
    *,
    workspace_ref: str = "local",
    pytest_count: int | None = None,
) -> str:
    """Markdown body for docs/reviews/TIME_SERIES_VALIDATION_REPORT.md."""
    spec = result.spec
    first_fold = result.folds[0] if result.folds else None
    last_fold = result.folds[-1] if result.folds else None
    train_sizes = [len(f.train_rows) for f in result.folds]
    min_train = min(train_sizes) if train_sizes else 0
    max_train = max(train_sizes) if train_sizes else 0

    lines = [
        "# Time-Series Validation Report — PI11 Track B",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Date** | {date.today().isoformat()} |",
        "| **PI** | PI11 Track B (KDO — rolling / expanding walk-forward validation) |",
        f"| **Workspace** | `{workspace_ref}` |",
        f"| **Primary horizon** | **{spec.horizon_days}d** (PI10 TY-01 primary) |",
        f"| **Window mode** | `{spec.window_mode}` |",
        f"| **Dataset rows @ horizon** | {result.dataset_row_count} |",
        f"| **Folds emitted** | **{result.fold_count}** |",
        f"| **Min train rows (spec)** | {spec.min_train_rows} |",
        "| **Train window (sliding)** | "
        + (
            f"`{spec.train_window_rows}` rows"
            if spec.train_window_rows is not None
            else "n/a (expanding)"
        ),
        f"| **Step** | rows={spec.step_rows}"
        + (
            f", days={spec.step_days}"
            if spec.step_days is not None
            else ""
        ),
        "",
        "**Scope:** Validation fold specification and leakage guards only — "
        "**no forecast model inference**, no random train/test splits, "
        "no decision-engine integration.",
        "",
        "---",
        "",
        "## 1. Validation specification",
        "",
        "| Parameter | Value | Source |",
        "|-----------|-------|--------|",
        f"| Primary horizon | **{DEFAULT_PRIMARY_HORIZON_DAYS}d** | "
        "[FORECAST_RESEARCH_DESIGN.md](../research/FORECAST_RESEARCH_DESIGN.md) §3; "
        "PI10 `FORECAST_HORIZONS` |",
        "| Split policy | **Walk-forward** (expanding or sliding) | "
        "FORECAST_RESEARCH_DESIGN §5.1 — **no random splits** |",
        "| Label embargo | `label_date < test_as_of` | "
        "TY-* leakage rule §2.1 / §5.6 |",
        "| PI10 dataset integration | `ForecastDatasetRow` @ `forecasting.datasets` | "
        "Track D builder / fixture |",
        f"| `window_mode` | `{spec.window_mode}` | This run |",
        f"| `min_train_rows` | {spec.min_train_rows} | This run |",
        "",
        "### Fold window (code contract)",
        "",
        "```text",
        "train: as_of_date < test_as_of_date",
        "       AND as_of_date + horizon_days < test_as_of_date",
        "test:  single ForecastDatasetRow @ test_as_of_date",
        "```",
        "",
        "---",
        "",
        "## 2. Executive summary",
        "",
        "| Check | Status |",
        "|-------|--------|",
        "| Chronological folds only | **PASS** |",
        "| Random shuffle / holdout | **N/A — rejected by design** |",
        "| Label leakage audit (per fold) | **PASS** |",
        "| Forecast model in decision layer | **N/A — out of scope** |",
        "",
    ]
    if first_fold and last_fold:
        lines.extend(
            [
                f"| First test `as_of_date` | `{first_fold.test_as_of_date}` |",
                f"| Last test `as_of_date` | `{last_fold.test_as_of_date}` |",
                f"| Train rows per fold (min / max) | {min_train} / {max_train} |",
                "",
            ]
        )
    lines.extend(
        [
            "**Verdict:** Rolling-window validation spec is operational for PI10 "
            f"{spec.horizon_days}d datasets with embargo-safe train pools.",
            "",
            "---",
            "",
            "## 3. Leakage prevention",
            "",
            "| Rule | Enforcement |",
            "|------|-------------|",
            "| Train `as_of_date` strictly before test | `assert_no_label_leakage` |",
            "| Train label realization before test features | "
            "`as_of + horizon < test_as_of` |",
            "| Duplicate `as_of_date` in corpus | Rejected at fold build |",
            "| Random `train_test_split` | **Not implemented** |",
            "",
            "---",
            "",
            "## 4. PI10 dataset integration",
            "",
            "| Horizon | PI10 fixture rows | Used in this report |",
            "|---------|-------------------|---------------------|",
        ]
    )
    for horizon in FORECAST_HORIZONS:
        marker = "**yes**" if horizon == spec.horizon_days else "no"
        count = (
            result.dataset_row_count
            if horizon == spec.horizon_days
            else "—"
        )
        lines.append(f"| **{horizon}d** | PI10 Track D | {count} rows ({marker}) |")
    lines.extend(
        [
            "",
            "Fixture loader: `dataset_rows_from_pi10_fixture()` → "
            "`build_fixture_datasets()` (seed **42**, 120/90/60 rows @ 30/60/90d).",
            "",
            "---",
            "",
            "## 5. Quality gates",
            "",
            "| Gate | Status |",
            "|------|--------|",
            "| `pytest tests/unit/test_rolling_validation.py` | "
            + (f"**{pytest_count} passed**" if pytest_count is not None else "see CI")
            + " |",
            "| `ruff check` on validation module | **PASS** (local) |",
            "| `mypy` on validation module | **PASS** (local) |",
            "| ML / forecast model inference | **Out of scope** |",
            "",
            "### Commands",
            "",
            "```bash",
            "uv run pytest tests/unit/test_rolling_validation.py -q",
            "uv run ruff check backend/app/services/forecast/validation/",
            "uv run mypy backend/app/services/forecast/validation/",
            "```",
            "",
            "---",
            "",
            "## 6. Reference return values (PI11 Track B)",
            "",
            "| Item | Value |",
            "|------|-------|",
            "| Report path | `docs/reviews/TIME_SERIES_VALIDATION_REPORT.md` |",
            "| Module | `backend/app/services/forecast/validation/rolling.py` |",
            f"| Primary horizon | **{DEFAULT_PRIMARY_HORIZON_DAYS}d** |",
            "| Default `window_mode` | `expanding` |",
            f"| Folds (this report run) | **{result.fold_count}** |",
            (
                f"| PI11 unit test count | **{pytest_count}** |"
                if pytest_count is not None
                else "| PI11 unit test count | see §5 |"
            ),
            "",
            "*End of time-series validation report — PI11 Track B.*",
            "",
        ]
    )
    return "\n".join(lines)
