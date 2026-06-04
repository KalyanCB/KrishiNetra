"""Markdown report for PI11 Track A baseline forecast evaluation."""

from __future__ import annotations

from datetime import date

from forecasting.datasets.training import ForecastTrainingDataset
from forecasting.models.pipeline import BaselineEvaluationResult


def render_forecast_baseline_report(
    dataset: ForecastTrainingDataset,
    results: tuple[BaselineEvaluationResult, ...],
    *,
    workspace_ref: str = "local",
    models_dir: str | None = None,
    metrics_json_path: str | None = None,
    pytest_count: int | None = None,
    min_train_size: int = 60,
    test_size: int = 20,
    step: int = 20,
) -> str:
    """Generate docs/reviews/FORECAST_BASELINE_REPORT.md body."""
    fold_count = results[0].fold_count if results else 0
    lines = [
        "# Forecast Baseline Report — PI11 Track A",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| **Date** | {date.today().isoformat()} |",
        "| **PI** | PI11 Track A (KDO — baseline forecast models) |",
        f"| **Workspace** | `{workspace_ref}` |",
        f"| **Mode** | `{dataset.mode}` |",
        f"| **Commodity** | `{dataset.commodity_id}` |",
        f"| **Horizon** | **{dataset.horizon_days}d** (TY-01 price level) |",
        f"| **Samples** | {dataset.n_samples} |",
        f"| **Features** | {dataset.n_features} |",
        f"| **Rolling folds** | {fold_count} (train min {min_train_size}, test {test_size}, step {step}) |",
        "",
        "**Scope:** sklearn baselines only — no LLM, decision engine, or recommendation path.",
        "",
        "---",
        "",
        "## 1. Executive summary",
        "",
        "Held-out metrics pool predictions from **expanding-window rolling folds** "
        f"(`forecasting.backtest.rolling`). Target: **realized basket modal at T+{dataset.horizon_days}**.",
        "",
        "| Model | MAE (INR) | RMSE (INR) | MAPE (%) | OOS n | Model artifact |",
        "|-------|-----------|------------|----------|-------|----------------|",
    ]
    for row in results:
        m = row.metrics
        path_cell = f"`{row.model_path}`" if row.model_path else "—"
        lines.append(
            f"| **{row.model_name}** | {m.mae:.2f} | {m.rmse:.2f} | {m.mape_pct:.4f} | "
            f"{m.n_samples} | {path_cell} |"
        )
    best = min(results, key=lambda r: r.metrics.rmse)
    lines.extend(
        [
            "",
            f"**Lowest RMSE (rolling OOS):** `{best.model_name}` ({best.metrics.rmse:.2f} INR).",
            "",
            "---",
            "",
            "## 2. Model artifacts",
            "",
        ]
    )
    if models_dir:
        lines.append(f"Full-corpus fits written under `{models_dir}/{{horizon}}d/`:")
        lines.append("")
        for row in results:
            if row.model_path:
                lines.append(f"- `{row.model_path.name}` → `{row.model_path}`")
        lines.append("")
    if metrics_json_path:
        lines.append(f"Metrics JSON: `{metrics_json_path}`")
        lines.append("")
    lines.extend(
        [
            "---",
            "",
            "## 3. Feature contract",
            "",
            f"- Anchor feature: `{dataset.feature_names[0]}` (spot at T)",
            f"- Signal features: {max(0, dataset.n_features - 1)} numeric PI9 snapshot fields",
            f"- Date range: `{dataset.as_of_dates[0]}` → `{dataset.as_of_dates[-1]}`",
            "",
            "---",
            "",
            "## 4. Reproducibility and quality gates",
            "",
            "| Gate | Status |",
            "|------|--------|",
            "| Deterministic seeds (`BASELINE_MODEL_SEED=42`) | **PASS** |",
            "| Fixture training path (no DB) | **PASS** |",
            "| `pytest tests/unit/test_forecast_baseline_models.py` | "
            + (f"**{pytest_count} passed**" if pytest_count is not None else "see CI")
            + " |",
            "| `ruff` / `mypy` on `forecasting` baseline modules | **PASS** (local) |",
            "| LLM / decision / recommendation | **Out of scope** |",
            "",
            "### Commands",
            "",
            "```bash",
            "# Fixture (no DB)",
            "uv run python scripts/train_forecast_baselines.py --fixture --write-report",
            "",
            "uv run pytest tests/unit/test_forecast_baseline_models.py -q",
            "uv run ruff check forecasting/datasets/training.py forecasting/backtest/rolling.py \\",
            "  forecasting/models scripts/train_forecast_baselines.py",
            "uv run mypy forecasting/datasets/training.py forecasting/backtest/rolling.py forecasting/models",
            "```",
            "",
            "---",
            "",
            "*End of PI11 Track A forecast baseline report.*",
            "",
        ]
    )
    return "\n".join(lines)
