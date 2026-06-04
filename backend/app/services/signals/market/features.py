"""Pure market signal feature math — deterministic, replayable (E-04-S01)."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from backend.app.services.signals.market.constants import (
    ARRIVAL_SEASON_MONTHS,
    DIRECTION_THRESHOLD,
    WEIGHT_ARRIVAL_MOMENTUM,
    WEIGHT_MSP_DISTANCE,
    WEIGHT_PRICE_ACCELERATION,
    WEIGHT_PRICE_MOMENTUM,
    ZSCORE_SCALE,
    MarketSignalType,
)
from shared.domain.enums import Direction

_FOUR_PLACES = Decimal("0.0001")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_FOUR_PLACES, rounding=ROUND_HALF_UP)


def _clip_unit(value: Decimal) -> Decimal:
    return _quantize(max(Decimal("0"), min(Decimal("1"), value)))


def _direction_from_value(
    value: float,
    *,
    invert: bool = False,
) -> Direction:
    """Map signed feature to direction; invert for supply-side features."""
    signed = -value if invert else value
    if signed > DIRECTION_THRESHOLD:
        return Direction.BULLISH
    if signed < -DIRECTION_THRESHOLD:
        return Direction.BEARISH
    return Direction.NEUTRAL


def _direction_sign(direction: Direction) -> int:
    if direction == Direction.BULLISH:
        return 1
    if direction == Direction.BEARISH:
        return -1
    return 0


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
    return _quantize(Decimal(str((float(value) - mean) / std)))


def normalized_zscore_magnitude(zscore: Decimal) -> Decimal:
    """Map |z| to [0, 1] using ZSCORE_SCALE."""
    return _clip_unit(abs(zscore) / Decimal(str(ZSCORE_SCALE)))


def arrival_season_gate(as_of_date: date) -> Decimal:
    """FG-01: arrival momentum active Oct–Mar only."""
    return Decimal("1") if as_of_date.month in ARRIVAL_SEASON_MONTHS else Decimal("0")


@dataclass(frozen=True, slots=True)
class FeatureSignal:
    """One deterministic market feature signal."""

    signal_type: MarketSignalType
    raw_value: Decimal
    direction: Direction
    magnitude: Decimal
    confidence_factor: Decimal

    def to_component(self) -> dict[str, str | float]:
        return {
            "signal_type": self.signal_type.value,
            "raw_value": float(self.raw_value),
            "direction": self.direction.value,
            "magnitude": float(self.magnitude),
            "confidence_factor": float(self.confidence_factor),
        }


def compute_price_momentum(
    *,
    basket_modals: dict[date, Decimal],
    as_of_date: date,
) -> FeatureSignal:
    """Z-score of basket modal vs 30d rolling window."""
    series = [basket_modals[d] for d in sorted(basket_modals) if d in basket_modals]
    today = basket_modals.get(as_of_date)
    if today is None or len(series) < 2:
        return FeatureSignal(
            signal_type=MarketSignalType.PRICE_MOMENTUM,
            raw_value=Decimal("0"),
            direction=Direction.NEUTRAL,
            magnitude=Decimal("0"),
            confidence_factor=Decimal("0"),
        )
    z = zscore_of(today, series)
    return FeatureSignal(
        signal_type=MarketSignalType.PRICE_MOMENTUM,
        raw_value=z,
        direction=_direction_from_value(float(z)),
        magnitude=normalized_zscore_magnitude(z),
        confidence_factor=Decimal("1") if len(series) >= 7 else Decimal("0.5"),
    )


def compute_arrival_momentum(
    *,
    basket_arrivals: dict[date, Decimal],
    as_of_date: date,
) -> FeatureSignal:
    """Z-score of basket arrival volume vs rolling window; FG-01 season gate."""
    series = [basket_arrivals[d] for d in sorted(basket_arrivals) if d in basket_arrivals]
    today = basket_arrivals.get(as_of_date)
    gate = arrival_season_gate(as_of_date)
    if today is None or len(series) < 2:
        return FeatureSignal(
            signal_type=MarketSignalType.ARRIVAL_MOMENTUM,
            raw_value=Decimal("0"),
            direction=Direction.NEUTRAL,
            magnitude=Decimal("0"),
            confidence_factor=Decimal("0"),
        )
    z = zscore_of(today, series)
    mag = _clip_unit(normalized_zscore_magnitude(z) * gate)
    return FeatureSignal(
        signal_type=MarketSignalType.ARRIVAL_MOMENTUM,
        raw_value=z,
        direction=_direction_from_value(float(z), invert=True),
        magnitude=mag,
        confidence_factor=gate if len(series) >= 7 else Decimal("0.5") * gate,
    )


def compute_price_vs_msp_distance(
    *,
    spot_modal: Decimal | None,
    msp_inr_quintal: Decimal,
    msp_proximity_pct: Decimal,
    msp_is_stub: bool,
) -> FeatureSignal:
    """Signed distance of spot modal from MSP (SIGNAL_MATH §5.2 / Policy coupling)."""
    if spot_modal is None or msp_inr_quintal <= 0:
        return FeatureSignal(
            signal_type=MarketSignalType.PRICE_VS_MSP_DISTANCE,
            raw_value=Decimal("0"),
            direction=Direction.NEUTRAL,
            magnitude=Decimal("0"),
            confidence_factor=Decimal("0"),
        )
    distance = _quantize((spot_modal - msp_inr_quintal) / msp_inr_quintal)
    proximity = max(msp_proximity_pct, Decimal("0.0001"))
    mag = _clip_unit(abs(distance) / proximity)
    # Below MSP supports floor (bullish); above MSP weakens floor narrative.
    direction = _direction_from_value(float(-distance))
    confidence = Decimal("0.65") if msp_is_stub else Decimal("0.75")
    return FeatureSignal(
        signal_type=MarketSignalType.PRICE_VS_MSP_DISTANCE,
        raw_value=distance,
        direction=direction,
        magnitude=mag,
        confidence_factor=confidence,
    )


def compute_price_acceleration(
    *,
    basket_modals: dict[date, Decimal],
    as_of_date: date,
) -> FeatureSignal:
    """Second difference of basket modal (momentum change)."""
    ordered = sorted(basket_modals)
    if as_of_date not in basket_modals or len(ordered) < 3:
        return FeatureSignal(
            signal_type=MarketSignalType.PRICE_ACCELERATION,
            raw_value=Decimal("0"),
            direction=Direction.NEUTRAL,
            magnitude=Decimal("0"),
            confidence_factor=Decimal("0"),
        )

    def momentum_at(idx: int) -> Decimal:
        prev_date = ordered[idx - 1]
        cur_date = ordered[idx]
        prev_val = basket_modals[prev_date]
        cur_val = basket_modals[cur_date]
        if prev_val == 0:
            return Decimal("0")
        return _quantize((cur_val - prev_val) / prev_val)

    idx = ordered.index(as_of_date)
    if idx < 2:
        return FeatureSignal(
            signal_type=MarketSignalType.PRICE_ACCELERATION,
            raw_value=Decimal("0"),
            direction=Direction.NEUTRAL,
            magnitude=Decimal("0"),
            confidence_factor=Decimal("0"),
        )

    accel_series: list[Decimal] = []
    for i in range(2, len(ordered)):
        m_t = momentum_at(i)
        m_prev = momentum_at(i - 1)
        accel_series.append(_quantize(m_t - m_prev))

    today_accel = accel_series[-1] if accel_series else Decimal("0")
    z = zscore_of(today_accel, accel_series) if len(accel_series) >= 2 else today_accel
    return FeatureSignal(
        signal_type=MarketSignalType.PRICE_ACCELERATION,
        raw_value=z,
        direction=_direction_from_value(float(z)),
        magnitude=normalized_zscore_magnitude(z),
        confidence_factor=Decimal("1") if len(accel_series) >= 5 else Decimal("0.5"),
    )


def composite_direction(features: Sequence[FeatureSignal]) -> Direction:
    """Weighted vote of component directions; tie → neutral (SIGNAL_MATH §3.3)."""
    weights = {
        MarketSignalType.PRICE_MOMENTUM: WEIGHT_PRICE_MOMENTUM,
        MarketSignalType.ARRIVAL_MOMENTUM: WEIGHT_ARRIVAL_MOMENTUM,
        MarketSignalType.PRICE_VS_MSP_DISTANCE: WEIGHT_MSP_DISTANCE,
        MarketSignalType.PRICE_ACCELERATION: WEIGHT_PRICE_ACCELERATION,
    }
    score = 0.0
    for feature in features:
        weight = weights.get(feature.signal_type, 0.0)
        score += weight * _direction_sign(feature.direction)
    if score > DIRECTION_THRESHOLD:
        return Direction.BULLISH
    if score < -DIRECTION_THRESHOLD:
        return Direction.BEARISH
    return Direction.NEUTRAL


def composite_magnitude(features: Sequence[FeatureSignal]) -> Decimal:
    """SIGNAL_MATH §3.4 with arrival season gate embedded in arrival magnitude."""
    weights = {
        MarketSignalType.PRICE_MOMENTUM: WEIGHT_PRICE_MOMENTUM,
        MarketSignalType.ARRIVAL_MOMENTUM: WEIGHT_ARRIVAL_MOMENTUM,
        MarketSignalType.PRICE_VS_MSP_DISTANCE: WEIGHT_MSP_DISTANCE,
        MarketSignalType.PRICE_ACCELERATION: WEIGHT_PRICE_ACCELERATION,
    }
    total = Decimal("0")
    for feature in features:
        weight = Decimal(str(weights.get(feature.signal_type, 0.0)))
        total += weight * feature.magnitude
    return _clip_unit(total)


def composite_confidence(
    *,
    features: Sequence[FeatureSignal],
    coverage_ratio: Decimal,
    lag_penalty: Decimal,
    msp_stub_penalty: Decimal,
    confidence_base: Decimal,
) -> Decimal:
    """SIGNAL_MATH §3.5."""
    if not features:
        return Decimal("0")
    feature_conf = sum(f.confidence_factor for f in features) / Decimal(len(features))
    raw = (
        confidence_base
        * coverage_ratio
        * feature_conf
        * (Decimal("1") - lag_penalty)
        * (Decimal("1") - msp_stub_penalty)
    )
    return _clip_unit(raw)


def signed_value(direction: Direction, magnitude: Decimal) -> Decimal:
    """value = sign(dir) × m (SIGNAL_MATH §3.6)."""
    sign = Decimal(str(_direction_sign(direction)))
    return _quantize(sign * magnitude)
