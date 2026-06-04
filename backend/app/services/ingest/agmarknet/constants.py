"""Agmarknet ingest constants — OGD resource and cotton label mapping."""

from __future__ import annotations

SOURCE_AGMARKNET = "agmarknet"
COTTON_COMMODITY_ID = "cotton"
DEFAULT_CURRENCY = "INR"
DEFAULT_PRICE_UNIT = "quintal"
DEFAULT_ARRIVAL_UNIT = "quintal"
TONNES_TO_QUINTAL = 10

OGD_RESOURCE_UUID = "9ef84268-d588-465a-a308-a864a43d0070"

# String labels → cotton (E-02 / AGMARKNET_DATA_PROOF §4).
COTTON_COMMODITY_LABELS: frozenset[str] = frozenset(
    {
        "Cotton",
        "Kapas",
        "Cotton (Unginned)",
        "Cotton-Bags",
        "Cotton-Loose",
    }
)

EXCLUDED_COMMODITY_LABELS: frozenset[str] = frozenset({"Cotton Seed"})
