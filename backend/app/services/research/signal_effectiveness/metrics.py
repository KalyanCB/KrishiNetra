"""Pure correlation helpers — no ML (PI10 Track E)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import correlation, mean, stdev

FORWARD_HORIZONS_DAYS: tuple[int, ...] = (7, 30)

TRACKED_SIGNALS: tuple[str, ...] = (
    "price_momentum",
    "arrival_momentum",
    "rainfall_shock",
    "temperature_stress",
)

MIN_PAIRS_FOR_CORRELATION = 3


@dataclass(frozen=True, slots=True)
class CorrelationResult:
    """Pearson and Spearman correlation for one signal × horizon."""

    signal: str
    horizon_days: int
    pearson_r: float | None
    spearman_rho: float | None
    sample_size: int
    mean_signal: float | None
    mean_forward_return: float | None

    @property
    def primary_r(self) -> float | None:
        """Prefer Pearson; fall back to Spearman when undefined."""
        return self.pearson_r if self.pearson_r is not None else self.spearman_rho


def compute_pct_forward_return(
    *,
    price_today: float,
    price_future: float,
) -> float | None:
    """Percent change in basket modal price over the forward horizon."""
    if price_today <= 0.0:
        return None
    return (price_future - price_today) / price_today


def _rank(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    idx = 0
    while idx < len(indexed):
        j = idx
        while j + 1 < len(indexed) and indexed[j + 1][1] == indexed[idx][1]:
            j += 1
        avg_rank = (idx + j) / 2.0 + 1.0
        for k in range(idx, j + 1):
            ranks[indexed[k][0]] = avg_rank
        idx = j + 1
    return ranks


def pearson_r(xs: list[float], ys: list[float]) -> float | None:
    """Population Pearson r; None when variance is zero or n < MIN_PAIRS."""
    if len(xs) != len(ys) or len(xs) < MIN_PAIRS_FOR_CORRELATION:
        return None
    if stdev(xs) == 0.0 or stdev(ys) == 0.0:
        return None
    return float(correlation(xs, ys))


def spearman_rho(xs: list[float], ys: list[float]) -> float | None:
    """Spearman rank correlation via Pearson on ranks."""
    if len(xs) != len(ys) or len(xs) < MIN_PAIRS_FOR_CORRELATION:
        return None
    return pearson_r(_rank(xs), _rank(ys))


def correlate_series(
    *,
    signal: str,
    horizon_days: int,
    signal_values: list[float],
    forward_returns: list[float],
) -> CorrelationResult:
    """Align paired lists and compute correlation metrics."""
    pairs = [
        (s, r)
        for s, r in zip(signal_values, forward_returns, strict=True)
        if math.isfinite(s) and math.isfinite(r)
    ]
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    return CorrelationResult(
        signal=signal,
        horizon_days=horizon_days,
        pearson_r=pearson_r(xs, ys),
        spearman_rho=spearman_rho(xs, ys),
        sample_size=len(pairs),
        mean_signal=mean(xs) if xs else None,
        mean_forward_return=mean(ys) if ys else None,
    )


def pick_best_worst(
    results: tuple[CorrelationResult, ...],
    *,
    horizon_days: int = 30,
) -> tuple[CorrelationResult | None, CorrelationResult | None]:
    """Best/worst by |Pearson r| at the chosen horizon (ties: higher raw r)."""
    scoped = [r for r in results if r.horizon_days == horizon_days and r.primary_r is not None]
    if not scoped:
        return None, None
    best = max(scoped, key=lambda r: (abs(r.primary_r or 0.0), r.primary_r or 0.0))
    worst = min(scoped, key=lambda r: (abs(r.primary_r or 0.0), r.primary_r or 0.0))
    return best, worst
