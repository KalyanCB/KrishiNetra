"""NASA POWER daily point API — proof-of-access spike client."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from backend.app.spike.weather.constants import (
    NASA_POWER_DAILY_URL,
    TELANGANA_COTTON_DISTRICTS,
    TelanganaCottonDistrict,
)

DEFAULT_PARAMETERS = ("PRECTOTCORR", "T2M", "RH2M")


@dataclass(frozen=True, slots=True)
class NasaPowerDailyPoint:
    """One day of agriculture-community meteorology at a lat/lon."""

    district: str
    latitude: float
    longitude: float
    observation_date: date
    precipitation_mm: float
    temperature_c: float
    relative_humidity_pct: float


class NasaPowerClient:
    """Minimal HTTPS client for NASA POWER daily point pulls."""

    def __init__(
        self,
        *,
        base_url: str = NASA_POWER_DAILY_URL,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout_seconds
        self._client = client

    def fetch_daily(
        self,
        district: TelanganaCottonDistrict,
        start: date,
        end: date,
        *,
        parameters: tuple[str, ...] = DEFAULT_PARAMETERS,
    ) -> list[NasaPowerDailyPoint]:
        payload = self._request(
            latitude=district.latitude,
            longitude=district.longitude,
            start=start,
            end=end,
            parameters=parameters,
        )
        return self._parse_daily_series(district, payload)

    def fetch_telangana_cotton_belt(
        self,
        start: date,
        end: date,
    ) -> dict[str, list[NasaPowerDailyPoint]]:
        return {
            district.name: self.fetch_daily(district, start, end)
            for district in TELANGANA_COTTON_DISTRICTS
        }

    def _request(
        self,
        *,
        latitude: float,
        longitude: float,
        start: date,
        end: date,
        parameters: tuple[str, ...],
    ) -> dict[str, Any]:
        params: dict[str, str | float] = {
            "parameters": ",".join(parameters),
            "community": "AG",
            "latitude": latitude,
            "longitude": longitude,
            "start": start.strftime("%Y%m%d"),
            "end": end.strftime("%Y%m%d"),
            "format": "JSON",
        }
        if self._client is not None:
            response = self._client.get(self._base_url, params=params)
        else:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(self._base_url, params=params)
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
        return payload

    @staticmethod
    def _parse_daily_series(
        district: TelanganaCottonDistrict,
        payload: dict[str, Any],
    ) -> list[NasaPowerDailyPoint]:
        parameter_block = payload["properties"]["parameter"]
        precipitation = parameter_block["PRECTOTCORR"]
        temperature = parameter_block["T2M"]
        humidity = parameter_block["RH2M"]
        fill_value = float(payload["header"]["fill_value"])

        points: list[NasaPowerDailyPoint] = []
        for day_key in sorted(precipitation):
            prec = float(precipitation[day_key])
            temp = float(temperature[day_key])
            rh = float(humidity[day_key])
            if prec == fill_value or temp == fill_value or rh == fill_value:
                continue
            points.append(
                NasaPowerDailyPoint(
                    district=district.name,
                    latitude=district.latitude,
                    longitude=district.longitude,
                    observation_date=date.fromisoformat(
                        f"{day_key[0:4]}-{day_key[4:6]}-{day_key[6:8]}"
                    ),
                    precipitation_mm=prec,
                    temperature_c=temp,
                    relative_humidity_pct=rh,
                )
            )
        return points
