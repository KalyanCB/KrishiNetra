"""Production Agmarknet ingest: OGD fetch → parse → map → dedupe → persist."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.app.services.ingest.agmarknet.client import (
    OgdAgmarknetClient,
    OgdClientConfig,
)
from backend.app.services.ingest.agmarknet.constants import COTTON_COMMODITY_ID
from backend.app.services.ingest.agmarknet.dedupe import (
    filter_new_arrival_drafts,
    filter_new_price_drafts,
)
from backend.app.services.ingest.agmarknet.mapper import (
    AgmarknetMapper,
    ArrivalObservationDraft,
    PriceObservationDraft,
)
from backend.app.services.ingest.agmarknet.market_lookup import (
    AgmarknetMarketLookup,
    load_market_lookup_from_seed,
)
from backend.app.services.ingest.agmarknet.parser import parse_ogd_response
from backend.app.services.ingest.agmarknet.persist import (
    persist_arrival_drafts,
    persist_price_drafts,
)


@dataclass(frozen=True, slots=True)
class AgmarknetIngestResult:
    """Counters from one ingest run."""

    ogd_rows_fetched: int
    ogd_rows_parsed: int
    price_drafts: int
    arrival_drafts: int
    prices_inserted: int
    arrivals_inserted: int
    prices_skipped_duplicate: int
    arrivals_skipped_duplicate: int

    @property
    def total_inserted(self) -> int:
        return self.prices_inserted + self.arrivals_inserted


class AgmarknetIngestPipeline:
    """Orchestrate Agmarknet OGD ingestion into observation tables."""

    def __init__(
        self,
        session: Session,
        *,
        mapper: AgmarknetMapper | None = None,
        market_lookup: AgmarknetMarketLookup | None = None,
        ogd_client: OgdAgmarknetClient | None = None,
        write_quality_snapshot: bool = True,
    ) -> None:
        lookup = market_lookup or load_market_lookup_from_seed()
        self._session = session
        self._mapper = mapper or AgmarknetMapper(lookup)
        self._ogd_client = ogd_client
        self._write_quality_snapshot = write_quality_snapshot

    def ingest_from_fixture(self, fixture_path: Path) -> AgmarknetIngestResult:
        """Ingest a local OGD JSON fixture (CI and manual runs without API key)."""
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        return self.ingest_ogd_payload(payload)

    def ingest_ogd_payload(self, payload: dict[str, Any]) -> AgmarknetIngestResult:
        """Parse, map, dedupe, and persist one OGD response envelope."""
        records = parse_ogd_response(payload)
        prices, arrivals = self._mapper.map_records(records)
        return self._persist_mapped(
            ogd_rows_fetched=len(records),
            ogd_rows_parsed=len(records),
            prices=prices,
            arrivals=arrivals,
        )

    def ingest_from_ogd(
        self,
        *,
        filters: dict[str, str] | None = None,
        commit: bool = True,
    ) -> AgmarknetIngestResult:
        """Fetch all OGD pages and ingest mapped cotton observations."""
        if self._ogd_client is None:
            msg = "OGD client is required for live API ingest"
            raise ValueError(msg)

        raw_rows = self._ogd_client.fetch_all(filters=filters)
        payload = {"records": raw_rows}
        records = parse_ogd_response(payload)
        prices, arrivals = self._mapper.map_records(records)
        result = self._persist_mapped(
            ogd_rows_fetched=len(raw_rows),
            ogd_rows_parsed=len(records),
            prices=prices,
            arrivals=arrivals,
        )
        if commit:
            self._session.commit()
        return result

    def _persist_mapped(
        self,
        *,
        ogd_rows_fetched: int,
        ogd_rows_parsed: int,
        prices: list[PriceObservationDraft],
        arrivals: list[ArrivalObservationDraft],
    ) -> AgmarknetIngestResult:
        price_dedupe = filter_new_price_drafts(self._session, prices)
        arrival_dedupe = filter_new_arrival_drafts(self._session, arrivals)

        prices_inserted = persist_price_drafts(self._session, price_dedupe.to_insert)
        arrivals_inserted = persist_arrival_drafts(
            self._session, arrival_dedupe.to_insert
        )
        if self._write_quality_snapshot:
            from backend.app.services.quality.snapshot_service import (
                DataQualitySnapshotService,
            )

            inserted = price_dedupe.to_insert + arrival_dedupe.to_insert
            batch = prices + arrivals
            source = inserted if inserted else batch
            as_of_dates = [d.as_of_date for d in source]
            anchor = max(as_of_dates) if as_of_dates else date.today()
            DataQualitySnapshotService(self._session).record_after_agmarknet_ingest(
                commodity_id=COTTON_COMMODITY_ID,
                as_of_date=anchor,
            )

        return AgmarknetIngestResult(
            ogd_rows_fetched=ogd_rows_fetched,
            ogd_rows_parsed=ogd_rows_parsed,
            price_drafts=len(prices),
            arrival_drafts=len(arrivals),
            prices_inserted=prices_inserted,
            arrivals_inserted=arrivals_inserted,
            prices_skipped_duplicate=price_dedupe.skipped,
            arrivals_skipped_duplicate=arrival_dedupe.skipped,
        )


def build_ogd_client(api_key: str) -> OgdAgmarknetClient:
    """Construct a production OGD client from an API key."""
    return OgdAgmarknetClient(OgdClientConfig(api_key=api_key))
