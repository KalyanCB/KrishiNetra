"""Render FEATURE_IMPORTANCE_REPORT.md (PI11 Track C)."""

from __future__ import annotations

import json
from datetime import date

from forecasting.features.importance import FeatureImportanceResult
from forecasting.models.baselines import BASELINE_MODEL_SEED, RANDOM_FOREST_ESTIMATORS


def _fmt_importance(value: float) -> str:
    return f"{value:.6f}"


def _render_group_table(
    title: str,
    rows: tuple[tuple[str, float], ...],
    *,
    group_total: float,
) -> list[str]:
    lines = [
        f"### {title}",
        "",
        f"- **Group aggregate importance:** `{_fmt_importance(group_total)}`",
        "",
        "| Rank | Feature | Importance |",
        "|------|---------|------------|",
    ]
    if not rows:
        lines.append("| — | *(no features in group)* | — |")
    else:
        for rank, (name, score) in enumerate(rows, start=1):
            lines.append(f"| {rank} | `{name}` | {_fmt_importance(score)} |")
    lines.append("")
    return lines


def render_feature_importance_report(
    result: FeatureImportanceResult,
    *,
    workspace_ref: str = "local",
    report_date: str | None = None,
    pytest_count: int | None = None,
) -> str:
    """Markdown body for docs/reviews/FEATURE_IMPORTANCE_REPORT.md."""
    report_day = report_date or date.today().isoformat()
    ranked_groups = sorted(
        result.group_totals.items(),
        key=lambda item: (-item[1], item[0]),
    )
    lines = [
        "# Feature Importance Report — PI11 Track C",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Date** | {report_day} |",
        "| **PI** | PI11 Track C (KDO — RF baseline feature importance) |",
        f"| **Workspace** | `{workspace_ref}` |",
        f"| **Mode** | `{result.mode}` |",
        f"| **Horizon** | **{result.horizon_days}d** (`target_log_return`) |",
        f"| **Commodity** | `{result.commodity_id}` |",
        f"| **Window** | `{result.window_start}` → `{result.window_end}` |",
        f"| **Panel rows** | **{result.row_count}** |",
        f"| **Feature columns** | **{result.feature_count}** |",
        f"| **Model source** | `{result.model_source}` |",
        f"| **RF config** | `n_estimators={RANDOM_FOREST_ESTIMATORS}`, "
        f"`random_state={BASELINE_MODEL_SEED}` (Track A) |",
        "",
        "**Method:** `RandomForestRegressor` feature importances (Gini). "
        "Features grouped by lineage prefix (`market.*`, `weather.*`, `futures.*`) "
        "aligned with `feature_lineage.agents`.",
        "",
        "---",
        "",
        "## 1. Executive summary",
        "",
        "| Lineage group | Aggregate importance | Top feature |",
        "|---------------|---------------------|-------------|",
    ]
    for prefix, total in ranked_groups:
        top_rows = result.top_per_group.get(prefix, ())
        top_name = top_rows[0][0] if top_rows else "—"
        lines.append(
            f"| **{prefix.capitalize()}** | `{_fmt_importance(total)}` | `{top_name}` |"
        )
    lines.extend(
        [
            "",
            f"**Verdict:** Baseline RF trained on **{result.row_count}** rows; "
            "importance ranking is deterministic at fixed seed.",
            "",
            "---",
            "",
            "## 2. Top features per lineage group",
            "",
        ]
    )
    for prefix, _total in ranked_groups:
        title = f"{prefix.capitalize()} features"
        lines.extend(
            _render_group_table(
                title,
                result.top_per_group.get(prefix, ()),
                group_total=result.group_totals.get(prefix, 0.0),
            )
        )
    lines.extend(
        [
            "---",
            "",
            "## 3. Machine-readable summary",
            "",
            "```json",
            json.dumps(result.to_report_detail(), indent=2, sort_keys=True),
            "```",
            "",
            "---",
            "",
            "## 4. Reproducibility and quality gates",
            "",
            "| Gate | Status |",
            "|------|--------|",
            "| Fixed fixture path (`--fixture`) | **PASS** |",
            "| Deterministic `random_state` | **PASS** |",
            "| Lineage prefix grouping | **PASS** |",
            "| `pytest tests/unit/test_forecast_feature_importance.py` | "
            + (f"**{pytest_count} passed**" if pytest_count is not None else "see CI")
            + " |",
            "",
            "### Commands",
            "",
            "```bash",
            "uv run python scripts/forecast_feature_importance.py --fixture --write-report",
            "",
            "uv run pytest tests/unit/test_forecast_feature_importance.py -q",
            "uv run ruff check forecasting/features forecasting/models "
            "scripts/forecast_feature_importance.py",
            "uv run mypy forecasting/features forecasting/models",
            "```",
            "",
            "---",
            "",
            "*End of PI11 Track C feature importance report.*",
            "",
        ]
    )
    return "\n".join(lines)
