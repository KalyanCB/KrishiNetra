"""IMD public REST API — proof-of-access feasibility probe."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from backend.app.spike.weather.constants import (
    IMD_DISTRICT_RAINFALL_URL,
    IMD_SAMPLE_OBJ_ID,
    IMD_STATE_RAINFALL_URL,
)


@dataclass(frozen=True, slots=True)
class ImdProbeResult:
    """Outcome of a single IMD endpoint access attempt."""

    endpoint: str
    status_code: int
    accessible: bool
    error_message: str | None
    sample_record_count: int
    notes: str


class ImdAccessProbe:
    """Documented-access test for IMD rainfall endpoints (no production ingest)."""

    def __init__(
        self,
        *,
        district_url: str = IMD_DISTRICT_RAINFALL_URL,
        state_url: str = IMD_STATE_RAINFALL_URL,
        timeout_seconds: float = 20.0,
        api_key: str | None = None,
        client: httpx.Client | None = None,
    ) -> None:
        self._district_url = district_url
        self._state_url = state_url
        self._timeout = timeout_seconds
        self._api_key = api_key
        self._client = client

    def probe_all(self) -> list[ImdProbeResult]:
        return [
            self.probe_district_rainfall(),
            self.probe_district_rainfall_by_id(IMD_SAMPLE_OBJ_ID),
            self.probe_state_rainfall(),
        ]

    def probe_district_rainfall(self) -> ImdProbeResult:
        return self._probe(self._district_url, "district_rainfall")

    def probe_district_rainfall_by_id(self, obj_id: str) -> ImdProbeResult:
        return self._probe(
            self._district_url,
            f"district_rainfall?id={obj_id}",
            params={"id": obj_id},
        )

    def probe_state_rainfall(self) -> ImdProbeResult:
        return self._probe(self._state_url, "state_rainfall")

    def _probe(
        self,
        url: str,
        label: str,
        *,
        params: dict[str, str] | None = None,
    ) -> ImdProbeResult:
        headers = self._build_headers()
        if self._client is not None:
            response = self._client.get(url, params=params, headers=headers)
        else:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url, params=params, headers=headers)

        body = self._safe_json(response)
        error_message = self._extract_error(body)
        sample_count = self._count_records(body)
        accessible = response.status_code == 200 and sample_count > 0

        notes = (
            "Requires IMD API key and/or IP whitelist per mausam.imd.gov.in/apis.php"
        )
        if response.status_code == 401 and error_message == "API key missing":
            notes = "401 API key missing — apply for key + IP whitelist before E-03 cron ingest"

        return ImdProbeResult(
            endpoint=label,
            status_code=response.status_code,
            accessible=accessible,
            error_message=error_message,
            sample_record_count=sample_count,
            notes=notes,
        )

    def _build_headers(self) -> dict[str, str]:
        if not self._api_key:
            return {}
        return {"Authorization": f"Bearer {self._api_key}"}

    @staticmethod
    def _safe_json(response: httpx.Response) -> dict[str, Any] | list[Any]:
        try:
            parsed = response.json()
        except ValueError:
            return {}
        if isinstance(parsed, dict | list):
            return parsed
        return {}

    @staticmethod
    def _extract_error(body: dict[str, Any] | list[Any]) -> str | None:
        if isinstance(body, dict) and "error" in body:
            value = body["error"]
            return str(value) if value is not None else None
        return None

    @staticmethod
    def _count_records(body: dict[str, Any] | list[Any]) -> int:
        if isinstance(body, list):
            return len(body)
        if isinstance(body, dict):
            for key in ("data", "records", "result"):
                value = body.get(key)
                if isinstance(value, list):
                    return len(value)
        return 0
