"""Telangana cotton belt reference points for weather spike probes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TelanganaCottonDistrict:
    """District centroid used for gridded weather pulls."""

    name: str
    latitude: float
    longitude: float
    imd_obj_id: str | None = None


TELANGANA_COTTON_DISTRICTS: tuple[TelanganaCottonDistrict, ...] = (
    TelanganaCottonDistrict("Khammam", 17.25, 79.75),
    TelanganaCottonDistrict("Warangal", 17.97, 79.59),
    TelanganaCottonDistrict("Karimnagar", 18.44, 79.13),
    TelanganaCottonDistrict("Nalgonda", 17.05, 79.27),
    TelanganaCottonDistrict("Mahabubabad", 17.60, 80.00),
)

# Documented sample OBJ_ID (Adilabad, Telangana-adjacent) from IMD feasibility research.
IMD_SAMPLE_OBJ_ID = "164"

NASA_POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
IMD_DISTRICT_RAINFALL_URL = "https://api.imd.gov.in/api/v1/districtrainfall"
IMD_STATE_RAINFALL_URL = "https://api.imd.gov.in/api/v1/staterainfall"
