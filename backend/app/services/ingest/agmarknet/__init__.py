"""Agmarknet OGD ingest — parser, mapper, OGD client, and production pipeline."""

from backend.app.services.ingest.agmarknet.client import (
    OgdAgmarknetClient,
    OgdApiError,
    OgdClientConfig,
    OgdPage,
)
from backend.app.services.ingest.agmarknet.mapper import (
    AgmarknetMapper,
    ArrivalObservationDraft,
    PriceObservationDraft,
)
from backend.app.services.ingest.agmarknet.market_lookup import (
    AgmarknetMarketKey,
    AgmarknetMarketLookup,
    load_market_lookup_from_seed,
)
from backend.app.services.ingest.agmarknet.parser import (
    AgmarknetParseError,
    AgmarknetRecord,
    parse_ogd_response,
    parse_record,
)
from backend.app.services.ingest.agmarknet.pipeline import (
    AgmarknetIngestPipeline,
    AgmarknetIngestResult,
    build_ogd_client,
)

__all__ = [
    "AgmarknetIngestPipeline",
    "AgmarknetIngestResult",
    "AgmarknetMapper",
    "AgmarknetMarketKey",
    "AgmarknetMarketLookup",
    "AgmarknetParseError",
    "AgmarknetRecord",
    "ArrivalObservationDraft",
    "OgdAgmarknetClient",
    "OgdApiError",
    "OgdClientConfig",
    "OgdPage",
    "PriceObservationDraft",
    "build_ogd_client",
    "load_market_lookup_from_seed",
    "parse_ogd_response",
    "parse_record",
]
