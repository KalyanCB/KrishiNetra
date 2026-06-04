"""Pure futures signal feature math — deterministic, replayable (E-04 F-04-05)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from backend.app.services.signals.common import clip_signed, clip_unit, quantize
from backend.app.services.signals.futures.constants import (
    CURVE_REGIME_THRESHOLD,
    DIRECTION_THRESHOLD,
    WEIGHT_BASIS,
    WEIGHT_CURVE_REGIME,
    WEIGHT_CURVE_SLOPE,
    WEIGHT_OPEN_INTEREST,
    ZSCORE_SCALE,
    CurveRegime,
    FuturesPrimaryDriver,
)
from shared.domain.enums import Direction


def zscore_of(value: Decimal, series: Sequence[Decimal]) -> Decimal:
    """Population z-score; returns 0 when variance is zero or series too short."""
    if len(series) < 2:
        return Decimal("0")
    values = [float(v) for v in series]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    if variance <= 0.0:
        return Decimal("0")
    std = variance**0.5
    return quantize(Decimal(str((float(value) - mean) / std)))


def normalized_zscore_magnitude(zscore: Decimal) -> Decimal:
    """Map |z| to [0, 1] using ZSCORE_SCALE."""
    return clip_unit(abs(zscore) / ZSCORE_SCALE)


def _direction_sign(direction: Direction) -> int:
    if direction == Direction.BULLISH:
        return 1
    if direction == Direction.BEARISH:
        return -1
    return 0


def _direction_from_value(value: Decimal, *, invert: bool = False) -> Direction:
    signed = -value if invert else value
    if signed > DIRECTION_THRESHOLD:
        return Direction.BULLISH
    if signed < -DIRECTION_THRESHOLD:
        return Direction.BEARISH
    return Direction.NEUTRAL


@dataclass(frozen=True, slots=True)
class FuturesFeatureSet:
    """Four deterministic futures sub-signals plus composite metadata."""

    curve_slope: Decimal
    basis_futures_spot: Decimal
    open_interest_change: Decimal
    curve_regime: CurveRegime
    primary_driver: FuturesPrimaryDriver
    direction: Direction
    magnitude: Decimal
    confidence: Decimal
    near_settle_quintal: Decimal | None
    far_settle_quintal: Decimal | None
    spot_modal_quintal: Decimal | None
    thin_oi_penalty: Decimal
    spot_gap_penalty: Decimal

    def as_components(self) -> dict[str, object]:
        return {
            "curve_slope": float(self.curve_slope),
            "basis_futures_spot": float(self.basis_futures_spot),
            "open_interest_change": float(self.open_interest_change),
            "curve_regime": self.curve_regime.value,
            "curve_regime_mi_eligible": False,
            "primary_driver": self.primary_driver.value,
            "near_settle_quintal": (
                float(self.near_settle_quintal)
                if self.near_settle_quintal is not None
                else None
            ),
            "far_settle_quintal": (
                float(self.far_settle_quintal)
                if self.far_settle_quintal is not None
                else None
            ),
            "spot_modal_quintal": (
                float(self.spot_modal_quintal)
                if self.spot_modal_quintal is not None
                else None
            ),
            "thin_oi_penalty": float(self.thin_oi_penalty),
            "spot_gap_penalty": float(self.spot_gap_penalty),
        }


def compute_curve_slope(
    *,
    near_settle: Decimal,
    far_settle: Decimal,
) -> Decimal:
    """Normalized (P_near - P_far) / P_near; backwardation → positive."""
    if near_settle <= 0:
        return Decimal("0")
    return quantize((near_settle - far_settle) / near_settle)


def compute_basis_futures_spot(
    *,
    near_settle_quintal: Decimal,
    spot_modal_quintal: Decimal | None,
) -> Decimal:
    """Signed pct (P_futures,near - P_spot) / P_spot."""
    if spot_modal_quintal is None or spot_modal_quintal <= 0:
        return Decimal("0")
    return quantize((near_settle_quintal - spot_modal_quintal) / spot_modal_quintal)


def compute_open_interest_change_zscore(
    *,
    oi_series: Sequence[int],
) -> Decimal:
    """Δ OI vs prior session z-scored over rolling window."""
    if len(oi_series) < 2:
        return Decimal("0")
    deltas: list[Decimal] = []
    for index in range(1, len(oi_series)):
        prior = oi_series[index - 1]
        current = oi_series[index]
        if prior <= 0:
            deltas.append(Decimal("0"))
        else:
            deltas.append(quantize(Decimal(str(current - prior)) / Decimal(str(prior))))
    today_delta = deltas[-1]
    return zscore_of(today_delta, deltas)


def classify_curve_regime(curve_slope: Decimal) -> CurveRegime:
    """Classify backwardation / contango / flat (G-07: dev logs only)."""
    if curve_slope > CURVE_REGIME_THRESHOLD:
        return CurveRegime.BACKWARDATION
    if curve_slope < -CURVE_REGIME_THRESHOLD:
        return CurveRegime.CONTANGO
    return CurveRegime.FLAT


def _component_directions(
    *,
    curve_slope: Decimal,
    basis: Decimal,
    oi_z: Decimal,
    regime: CurveRegime,
) -> dict[FuturesPrimaryDriver, Direction]:
    return {
        FuturesPrimaryDriver.CURVE_SLOPE: _direction_from_value(curve_slope),
        FuturesPrimaryDriver.BASIS: _direction_from_value(basis),
        FuturesPrimaryDriver.OPEN_INTEREST: _direction_from_value(oi_z),
        FuturesPrimaryDriver.CURVE_REGIME: _regime_direction(regime),
    }


def _regime_direction(regime: CurveRegime) -> Direction:
    if regime == CurveRegime.BACKWARDATION:
        return Direction.BULLISH
    if regime == CurveRegime.CONTANGO:
        return Direction.BEARISH
    return Direction.NEUTRAL


def select_primary_driver(
    *,
    curve_slope: Decimal,
    basis: Decimal,
    oi_z: Decimal,
    regime: CurveRegime,
) -> FuturesPrimaryDriver:
    """Pick driver with largest weighted |component| (SIGNAL_ENGINE_V1 §6.3)."""
    candidates: list[tuple[FuturesPrimaryDriver, Decimal]] = [
        (FuturesPrimaryDriver.CURVE_SLOPE, abs(curve_slope) * Decimal(str(WEIGHT_CURVE_SLOPE))),
        (FuturesPrimaryDriver.BASIS, abs(basis) * Decimal(str(WEIGHT_BASIS))),
        (
            FuturesPrimaryDriver.OPEN_INTEREST,
            normalized_zscore_magnitude(oi_z) * Decimal(str(WEIGHT_OPEN_INTEREST)),
        ),
        (
            FuturesPrimaryDriver.CURVE_REGIME,
            _regime_magnitude(regime) * Decimal(str(WEIGHT_CURVE_REGIME)),
        ),
    ]
    candidates.sort(key=lambda item: (item[1], item[0].value), reverse=True)
    return candidates[0][0]


def _regime_magnitude(regime: CurveRegime) -> Decimal:
    if regime == CurveRegime.FLAT:
        return Decimal("0")
    return Decimal("1")


def composite_direction(
    *,
    primary_driver: FuturesPrimaryDriver,
    curve_slope: Decimal,
    basis: Decimal,
    oi_z: Decimal,
    regime: CurveRegime,
) -> Direction:
    """Direction follows primary_driver when |component| > threshold; else weighted vote."""
    directions = _component_directions(
        curve_slope=curve_slope,
        basis=basis,
        oi_z=oi_z,
        regime=regime,
    )
    primary_dir = directions[primary_driver]
    if primary_dir != Direction.NEUTRAL:
        return primary_dir

    weights = {
        FuturesPrimaryDriver.CURVE_SLOPE: WEIGHT_CURVE_SLOPE,
        FuturesPrimaryDriver.BASIS: WEIGHT_BASIS,
        FuturesPrimaryDriver.OPEN_INTEREST: WEIGHT_OPEN_INTEREST,
        FuturesPrimaryDriver.CURVE_REGIME: WEIGHT_CURVE_REGIME,
    }
    score = Decimal("0")
    for driver, direction in directions.items():
        score += Decimal(str(weights[driver])) * Decimal(str(_direction_sign(direction)))
    if score > DIRECTION_THRESHOLD:
        return Direction.BULLISH
    if score < -DIRECTION_THRESHOLD:
        return Direction.BEARISH
    return Direction.NEUTRAL


def composite_magnitude(
    *,
    curve_slope: Decimal,
    basis: Decimal,
    oi_z: Decimal,
    regime: CurveRegime,
) -> Decimal:
    """SIGNAL_ENGINE_V1 §6.4 weighted clip."""
    total = (
        Decimal(str(WEIGHT_CURVE_SLOPE)) * clip_signed(curve_slope).copy_abs()
        + Decimal(str(WEIGHT_BASIS)) * clip_signed(basis).copy_abs()
        + Decimal(str(WEIGHT_OPEN_INTEREST)) * normalized_zscore_magnitude(oi_z)
        + Decimal(str(WEIGHT_CURVE_REGIME)) * _regime_magnitude(regime)
    )
    return clip_unit(total)


def composite_confidence(
    *,
    feed_factor: Decimal,
    thin_oi_penalty: Decimal,
    spot_gap_penalty: Decimal,
    confidence_base: Decimal,
    confidence_cap: Decimal,
) -> Decimal:
    """SIGNAL_ENGINE_V1 §6.5 with prototype cap (G-03)."""
    raw = (
        confidence_base
        * feed_factor
        * (Decimal("1") - thin_oi_penalty)
        * (Decimal("1") - spot_gap_penalty)
    )
    return clip_unit(min(raw, confidence_cap))


def compute_futures_features(
    *,
    near_settle_quintal: Decimal | None,
    far_settle_quintal: Decimal | None,
    spot_modal_quintal: Decimal | None,
    oi_series: Sequence[int],
    futures_feed_ok: bool,
    confidence_base: Decimal,
    confidence_cap: Decimal,
    thin_oi_threshold: int,
    thin_oi_penalty_rate: Decimal,
) -> FuturesFeatureSet:
    """Compute four futures transforms and composite direction/magnitude/confidence."""
    if near_settle_quintal is None or far_settle_quintal is None:
        return _empty_features(
            spot_modal_quintal=spot_modal_quintal,
            confidence_base=confidence_base,
            confidence_cap=confidence_cap,
        )

    curve_slope = compute_curve_slope(
        near_settle=near_settle_quintal,
        far_settle=far_settle_quintal,
    )
    basis = compute_basis_futures_spot(
        near_settle_quintal=near_settle_quintal,
        spot_modal_quintal=spot_modal_quintal,
    )
    oi_z = compute_open_interest_change_zscore(oi_series=oi_series)
    regime = classify_curve_regime(curve_slope)
    primary = select_primary_driver(
        curve_slope=curve_slope,
        basis=basis,
        oi_z=oi_z,
        regime=regime,
    )
    direction = composite_direction(
        primary_driver=primary,
        curve_slope=curve_slope,
        basis=basis,
        oi_z=oi_z,
        regime=regime,
    )
    magnitude = composite_magnitude(
        curve_slope=curve_slope,
        basis=basis,
        oi_z=oi_z,
        regime=regime,
    )

    latest_oi = oi_series[-1] if oi_series else 0
    thin_oi_penalty = (
        thin_oi_penalty_rate
        if latest_oi > 0 and latest_oi < thin_oi_threshold
        else Decimal("0")
    )
    spot_gap_penalty = Decimal("0.20") if spot_modal_quintal is None else Decimal("0")
    feed_factor = Decimal("1") if futures_feed_ok else Decimal("0.35")

    confidence = composite_confidence(
        feed_factor=feed_factor,
        thin_oi_penalty=thin_oi_penalty,
        spot_gap_penalty=spot_gap_penalty,
        confidence_base=confidence_base,
        confidence_cap=confidence_cap,
    )

    return FuturesFeatureSet(
        curve_slope=curve_slope,
        basis_futures_spot=basis,
        open_interest_change=oi_z,
        curve_regime=regime,
        primary_driver=primary,
        direction=direction,
        magnitude=magnitude,
        confidence=confidence,
        near_settle_quintal=near_settle_quintal,
        far_settle_quintal=far_settle_quintal,
        spot_modal_quintal=spot_modal_quintal,
        thin_oi_penalty=thin_oi_penalty,
        spot_gap_penalty=spot_gap_penalty,
    )


def _empty_features(
    *,
    spot_modal_quintal: Decimal | None,
    confidence_base: Decimal,
    confidence_cap: Decimal,
) -> FuturesFeatureSet:
    spot_gap_penalty = Decimal("0.20") if spot_modal_quintal is None else Decimal("0")
    confidence = composite_confidence(
        feed_factor=Decimal("0.35"),
        thin_oi_penalty=Decimal("0"),
        spot_gap_penalty=spot_gap_penalty,
        confidence_base=confidence_base,
        confidence_cap=confidence_cap,
    )
    return FuturesFeatureSet(
        curve_slope=Decimal("0"),
        basis_futures_spot=Decimal("0"),
        open_interest_change=Decimal("0"),
        curve_regime=CurveRegime.FLAT,
        primary_driver=FuturesPrimaryDriver.CURVE_SLOPE,
        direction=Direction.NEUTRAL,
        magnitude=Decimal("0"),
        confidence=confidence,
        near_settle_quintal=None,
        far_settle_quintal=None,
        spot_modal_quintal=spot_modal_quintal,
        thin_oi_penalty=Decimal("0"),
        spot_gap_penalty=spot_gap_penalty,
    )
