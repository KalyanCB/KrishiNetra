"""Deterministic PI11 feature-importance panel fixtures."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from backend.app.persistence.models.signal import StructuredSignalModel
from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID
from forecasting.datasets.fixtures import (
    FIXTURE_REGISTRY_ID,
    FIXTURE_WINDOW_START,
)
from shared.domain.enums import AgentType, Direction


def _day_offset(obs_date: date) -> int:
    return (obs_date - FIXTURE_WINDOW_START).days


def fixture_market_signal(*, as_of_date: date) -> StructuredSignalModel:
    offset = _day_offset(as_of_date)
    return StructuredSignalModel(
        signal_id=uuid4(),
        agent_type=AgentType.MARKET.value,
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=as_of_date,
        as_of_timestamp=datetime(
            as_of_date.year, as_of_date.month, as_of_date.day, 12, 0, tzinfo=UTC
        ),
        value=Decimal("0.40") + Decimal(offset) * Decimal("0.001"),
        direction=Direction.BULLISH.value,
        magnitude=Decimal("0.50") + Decimal(offset) * Decimal("0.0005"),
        confidence=Decimal("0.70"),
        signal_components={
            "price_momentum": round(0.2 + offset * 0.01, 6),
            "arrival_momentum": round(0.05 + offset * 0.002, 6),
        },
        registry_id=FIXTURE_REGISTRY_ID,
        agent_version="market-v1.0.0-fixture",
    )


def fixture_weather_signal(*, as_of_date: date) -> StructuredSignalModel:
    offset = _day_offset(as_of_date)
    return StructuredSignalModel(
        signal_id=uuid4(),
        agent_type=AgentType.WEATHER.value,
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=as_of_date,
        as_of_timestamp=datetime(
            as_of_date.year, as_of_date.month, as_of_date.day, 12, 0, tzinfo=UTC
        ),
        value=Decimal("-0.10") - Decimal(offset) * Decimal("0.0008"),
        direction=Direction.BEARISH.value if offset % 2 == 0 else Direction.NEUTRAL.value,
        magnitude=Decimal("0.35"),
        confidence=Decimal("0.65"),
        signal_components={
            "rainfall_deviation": round(-0.1 - offset * 0.003, 6),
            "temperature_stress": round(0.05 + offset * 0.001, 6),
        },
        registry_id=FIXTURE_REGISTRY_ID,
        agent_version="weather-v1.0.0-fixture",
    )


def fixture_futures_signal(*, as_of_date: date) -> StructuredSignalModel:
    offset = _day_offset(as_of_date)
    return StructuredSignalModel(
        signal_id=uuid4(),
        agent_type=AgentType.FUTURES.value,
        commodity_id=COTTON_COMMODITY_ID,
        as_of_date=as_of_date,
        as_of_timestamp=datetime(
            as_of_date.year, as_of_date.month, as_of_date.day, 12, 0, tzinfo=UTC
        ),
        value=Decimal("0.05") + Decimal(offset) * Decimal("0.0004"),
        direction=Direction.BULLISH.value,
        magnitude=Decimal("0.20"),
        confidence=Decimal("0.30"),
        signal_components={
            "curve_slope": round(0.01 + offset * 0.0002, 8),
            "basis_futures_spot": round(-0.02 + offset * 0.0001, 8),
        },
        registry_id=FIXTURE_REGISTRY_ID,
        agent_version="futures-v1.0.0-prototype-fixture",
    )
