"""Map parsed Agmarknet rows to observation drafts (spike only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal

from backend.app.persistence.models.observation import ObservationValidationStatus
from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    COTTON_COMMODITY_LABELS,
    DEFAULT_ARRIVAL_UNIT,
    DEFAULT_CURRENCY,
    DEFAULT_PRICE_UNIT,
    EXCLUDED_COMMODITY_LABELS,
    SOURCE_AGMARKNET,
    TONNES_TO_QUINTAL,
)
from backend.app.services.ingest.agmarknet.market_lookup import AgmarknetMarketLookup
from backend.app.services.ingest.agmarknet.parser import AgmarknetRecord


@dataclass(frozen=True, slots=True)
class PriceObservationDraft:
    """Logical price_observation row before ORM persist."""

    market_id: str
    commodity_id: str
    price_type: str
    value: Decimal
    unit: str
    currency: str
    as_of_date: date
    observed_at: datetime
    source: str
    quality_grade: str | None
    validation_status: str


@dataclass(frozen=True, slots=True)
class ArrivalObservationDraft:
    """Logical arrival_observation row before ORM persist."""

    market_id: str
    commodity_id: str
    volume: Decimal
    unit: str
    as_of_date: date
    observed_at: datetime
    source: str
    validation_status: str


class AgmarknetMapper:
    """Map cotton Agmarknet records to price and arrival observation drafts."""

    def __init__(
        self,
        market_lookup: AgmarknetMarketLookup,
        *,
        commodity_id: str = COTTON_COMMODITY_ID,
        source: str = SOURCE_AGMARKNET,
    ) -> None:
        self._market_lookup = market_lookup
        self._commodity_id = commodity_id
        self._source = source

    def map_record(
        self,
        record: AgmarknetRecord,
        *,
        observed_at: datetime | None = None,
    ) -> tuple[list[PriceObservationDraft], ArrivalObservationDraft | None]:
        """
        Map one parsed row to observation drafts.

        Returns empty prices and no arrival when commodity is not cotton or market
        is unknown.
        """
        commodity_id = resolve_commodity_id(record.commodity)
        if commodity_id is None:
            return [], None

        market_id = self._market_lookup.resolve(
            state=record.state,
            district=record.district,
            market=record.market,
        )
        if market_id is None:
            return [], None

        observed = observed_at or _default_observed_at(record.arrival_date)
        quality = _quality_grade(record)
        prices = self._map_prices(
            record,
            market_id=market_id,
            commodity_id=commodity_id,
            observed_at=observed,
            quality_grade=quality,
        )
        arrival = self._map_arrival(
            record,
            market_id=market_id,
            commodity_id=commodity_id,
            observed_at=observed,
        )
        return prices, arrival

    def map_records(
        self,
        records: list[AgmarknetRecord],
        *,
        observed_at: datetime | None = None,
    ) -> tuple[list[PriceObservationDraft], list[ArrivalObservationDraft]]:
        all_prices: list[PriceObservationDraft] = []
        all_arrivals: list[ArrivalObservationDraft] = []
        for record in records:
            prices, arrival = self.map_record(record, observed_at=observed_at)
            all_prices.extend(prices)
            if arrival is not None:
                all_arrivals.append(arrival)
        return all_prices, all_arrivals

    def _map_prices(
        self,
        record: AgmarknetRecord,
        *,
        market_id: str,
        commodity_id: str,
        observed_at: datetime,
        quality_grade: str | None,
    ) -> list[PriceObservationDraft]:
        drafts: list[PriceObservationDraft] = []
        for price_type, value in (
            ("modal", record.modal_price),
            ("min", record.min_price),
            ("max", record.max_price),
        ):
            if value is None:
                continue
            drafts.append(
                PriceObservationDraft(
                    market_id=market_id,
                    commodity_id=commodity_id,
                    price_type=price_type,
                    value=value,
                    unit=DEFAULT_PRICE_UNIT,
                    currency=DEFAULT_CURRENCY,
                    as_of_date=record.arrival_date,
                    observed_at=observed_at,
                    source=self._source,
                    quality_grade=quality_grade,
                    validation_status=ObservationValidationStatus.RECEIVED.value,
                )
            )
        return drafts

    def _map_arrival(
        self,
        record: AgmarknetRecord,
        *,
        market_id: str,
        commodity_id: str,
        observed_at: datetime,
    ) -> ArrivalObservationDraft | None:
        if record.arrival_tonnes is None:
            return None
        volume_quintals = record.arrival_tonnes * TONNES_TO_QUINTAL
        return ArrivalObservationDraft(
            market_id=market_id,
            commodity_id=commodity_id,
            volume=volume_quintals,
            unit=DEFAULT_ARRIVAL_UNIT,
            as_of_date=record.arrival_date,
            observed_at=observed_at,
            source=self._source,
            validation_status=ObservationValidationStatus.RECEIVED.value,
        )


def resolve_commodity_id(commodity_label: str) -> str | None:
    """Map OGD commodity string to E-02 commodity_id; None if excluded/unknown."""
    label = commodity_label.strip()
    if label in EXCLUDED_COMMODITY_LABELS:
        return None
    if label in COTTON_COMMODITY_LABELS:
        return COTTON_COMMODITY_ID
    return None


def _quality_grade(record: AgmarknetRecord) -> str | None:
    parts = [p for p in (record.variety, record.grade) if p]
    if not parts:
        return None
    return "|".join(parts)


def _default_observed_at(as_of: date) -> datetime:
    """Post-mandi close placeholder (18:30 UTC example from data proof §7.1)."""
    return datetime(
        as_of.year,
        as_of.month,
        as_of.day,
        18,
        30,
        tzinfo=UTC,
    )
