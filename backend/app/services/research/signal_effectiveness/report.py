"""Render SIGNAL_EFFECTIVENESS_REPORT.md (PI10 Track E)."""

from __future__ import annotations

import json

from backend.app.services.research.signal_effectiveness.analysis import (
    SignalEffectivenessResult,
)
from backend.app.services.research.signal_effectiveness.metrics import (
    FORWARD_HORIZONS_DAYS,
    TRACKED_SIGNALS,
)


def _fmt_r(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:+.4f}"


def _fmt_signal_result(result: SignalEffectivenessResult, label: str) -> str:
    item = result.best_signal if label == "best" else result.worst_signal
    if item is None:
        return "— (insufficient pairs)"
    return (
        f"**{item.signal}** @ {item.horizon_days}d — "
        f"Pearson **{_fmt_r(item.pearson_r)}**, "
        f"Spearman **{_fmt_r(item.spearman_rho)}**, "
        f"n=**{item.sample_size}**"
    )


def render_signal_effectiveness_report_markdown(
    *,
    result: SignalEffectivenessResult,
    report_date: str = "2026-06-04",
) -> str:
    """Render PI10 Track E effectiveness report body."""
    lines = [
        "# Signal Effectiveness Report — PI10 Track E",
        "",
        f"**Date:** {report_date}",
        "**PI:** PI10 Track E (KDO — statistical correlation vs forward cotton prices)",
        "**Method:** Pearson + Spearman correlation; **no ML**",
        f"**Data source:** `{result.data_source}`",
        "",
        "---",
        "",
        "## 1. Verdict",
        "",
        "| Question | Answer |",
        "|----------|--------|",
        f"| Analysis window | `{result.window_start}` → `{result.window_end}` |",
        f"| Evaluable days (panel) | **{result.panel_summary.get('evaluable_days', 0)}** |",
        f"| Validated price rows loaded | **{result.price_observation_count}** |",
        f"| Arrival rows loaded | **{result.arrival_observation_count}** |",
        f"| Weather rows loaded | **{result.weather_observation_count}** |",
        f"| Primary markets | **{result.primary_market_count}** TG basket |",
        f"| Best signal @ {result.ranking_horizon_days}d (|r|) | {_fmt_signal_result(result, 'best')} |",
        f"| Weakest signal @ {result.ranking_horizon_days}d (|r|) | {_fmt_signal_result(result, 'worst')} |",
        "",
        "Forward target: **basket modal** percent change from validated `price_observation` "
        "(median of primary-market modal medians). Horizons: **7d**, **30d**.",
        "",
        "---",
        "",
        "## 2. Sample sizes",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| Evaluable calendar days | **{result.panel_summary.get('evaluable_days', 0)}** |",
    ]

    for signal in TRACKED_SIGNALS:
        lines.append(
            f"| `{signal}` non-null signal days | "
            f"**{result.panel_summary.get(signal, 0)}** |"
        )
    for horizon in FORWARD_HORIZONS_DAYS:
        key = f"forward_{horizon}d"
        lines.append(
            f"| Forward return `{horizon}d` non-null | "
            f"**{result.panel_summary.get(key, 0)}** |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Correlation matrix",
            "",
            "| Signal | Horizon | n | Pearson r | Spearman ρ | Mean signal | Mean fwd return |",
            "|--------|---------|---|-----------|------------|-------------|-----------------|",
        ]
    )

    for row in result.correlations:
        lines.append(
            f"| `{row.signal}` | {row.horizon_days}d | **{row.sample_size}** | "
            f"{_fmt_r(row.pearson_r)} | {_fmt_r(row.spearman_rho)} | "
            f"{_fmt_r(row.mean_signal)} | {_fmt_r(row.mean_forward_return)} |"
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 4. Interpretation notes",
            "",
            "- **Price momentum** — z-score of basket modal vs 30d rolling window; "
            "expect positive correlation with forward returns in trending regimes.",
            "- **Arrival momentum** — z-score of basket arrivals (Oct–Mar gate); "
            "supply-side invert; weak correlation is common in sparse arrival panels.",
            "- **Rainfall shock** — |today − prior 7d mean| / max(prior mean, 5 mm); "
            "[0, 1] weather spike feature.",
            "- **Temperature stress** — |T_mean − 28°C| / 10°C; [0, 1] heat/cold stress.",
            "",
            "Ranking uses **|Pearson r|** at the **30d** horizon unless sample size "
            "forces fallback to 7d pairs.",
            "",
            "---",
            "",
            "## 5. Deliverables",
            "",
            "| Artifact | Path |",
            "|----------|------|",
            "| Analysis module | `backend/app/services/research/signal_effectiveness/` |",
            "| CLI | `scripts/signal_effectiveness_analysis.py` |",
            "| Unit tests | `tests/unit/test_signal_effectiveness.py` |",
            "| Synthetic panel | `backend/app/services/research/signal_effectiveness/synthetic_panel.py` |",
            "",
            "---",
            "",
            "## 6. Reproduce",
            "",
            "```bash",
            "DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \\",
            "  uv run python scripts/signal_effectiveness_analysis.py --write-report",
            "",
            "uv run pytest tests/unit/test_signal_effectiveness.py -q",
            "```",
            "",
            "---",
            "",
            "## 7. Metrics payload",
            "",
            "```json",
            json.dumps(result.to_report_detail(), indent=2),
            "```",
            "",
            "*End of signal effectiveness report — PI10 Track E.*",
            "",
        ]
    )
    return "\n".join(lines)
