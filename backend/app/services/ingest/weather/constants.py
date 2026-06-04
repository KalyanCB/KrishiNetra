"""NASA POWER ingest constants — Telangana cotton belt (WEATHER_SPIKE_REPORT)."""

from __future__ import annotations

from backend.app.spike.weather.constants import (
    TELANGANA_COTTON_DISTRICTS,
    TelanganaCottonDistrict,
)

COTTON_COMMODITY_ID = "cotton"
WEATHER_SOURCE_NASA_POWER = "nasa_power"
DEFAULT_BACKFILL_MONTHS = 36
# NASA POWER T−4 latency observed in PI5 spike (2026-06-04).
NASA_POWER_END_LAG_DAYS = 4

# District name → E-02 region_id (cotton seed + weather belt extensions).
DISTRICT_REGION_IDS: dict[str, str] = {
    "Khammam": "reg_tg_khammam",
    "Warangal": "reg_tg_warangal",
    "Karimnagar": "reg_tg_karimnagar",
    "Nalgonda": "reg_tg_nalgonda",
    "Mahabubabad": "reg_tg_mahabubabad",
}


def district_for_region(region_id: str) -> TelanganaCottonDistrict | None:
    """Resolve spike centroid config for a cotton region id."""
    for district in TELANGANA_COTTON_DISTRICTS:
        if DISTRICT_REGION_IDS.get(district.name) == region_id:
            return district
    return None


def region_id_for_district(name: str) -> str:
    """Map district label to persisted region_id."""
    try:
        return DISTRICT_REGION_IDS[name]
    except KeyError as exc:
        msg = f"unknown weather district {name!r}"
        raise ValueError(msg) from exc
