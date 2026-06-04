"""Unit tests for PI5 Track D weather proof-of-access spike."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import httpx
import pytest

from backend.app.spike.weather.constants import TelanganaCottonDistrict
from backend.app.spike.weather.imd import ImdAccessProbe
from backend.app.spike.weather.nasa_power import NasaPowerClient


def _nasa_power_payload(start: str, end: str) -> dict[str, object]:
    return {
        "header": {"fill_value": -999.0, "start": start, "end": end},
        "properties": {
            "parameter": {
                "PRECTOTCORR": {start: 3.28, end: 0.0},
                "T2M": {start: 31.2, end: 32.1},
                "RH2M": {start: 68.0, end: 55.0},
            }
        },
    }


def test_nasa_power_client_parses_daily_series() -> None:
    district = TelanganaCottonDistrict("Khammam", 17.25, 79.75)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = _nasa_power_payload("20240601", "20240602")

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    client = NasaPowerClient(client=mock_client)
    points = client.fetch_daily(
        district,
        date(2024, 6, 1),
        date(2024, 6, 2),
    )

    assert len(points) == 2
    assert points[0].district == "Khammam"
    assert points[0].precipitation_mm == 3.28
    assert points[1].temperature_c == 32.1


def test_nasa_power_client_skips_fill_values() -> None:
    district = TelanganaCottonDistrict("Warangal", 17.97, 79.59)
    payload = _nasa_power_payload("20240601", "20240602")
    params = payload["properties"]["parameter"]
    assert isinstance(params, dict)
    params["PRECTOTCORR"]["20240602"] = -999.0

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.raise_for_status = MagicMock()
    mock_response.json.return_value = payload

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    client = NasaPowerClient(client=mock_client)
    points = client.fetch_daily(
        district,
        date(2024, 6, 1),
        date(2024, 6, 2),
    )

    assert len(points) == 1
    assert points[0].observation_date == date(2024, 6, 1)


def test_imd_probe_reports_api_key_missing() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = {"error": "API key missing"}

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    probe = ImdAccessProbe(client=mock_client)
    result = probe.probe_district_rainfall()

    assert result.status_code == 401
    assert result.accessible is False
    assert result.error_message == "API key missing"
    assert "401 API key missing" in result.notes


def test_imd_probe_marks_success_when_records_present() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "data": [
            {
                "OBJ_ID": "164",
                "District": "ADILABAD",
                "Date": "2023-01-31",
                "Daily Actual": "0.00",
            }
        ]
    }

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    probe = ImdAccessProbe(api_key="test-key", client=mock_client)
    result = probe.probe_district_rainfall()

    assert result.accessible is True
    assert result.sample_record_count == 1
    assert result.error_message is None


@pytest.mark.integration
def test_nasa_power_live_access() -> None:
    """Live NASA POWER call — open API, no credentials."""
    district = TelanganaCottonDistrict("Khammam", 17.25, 79.75)
    client = NasaPowerClient()
    points = client.fetch_daily(district, date(2024, 6, 1), date(2024, 6, 1))
    assert len(points) == 1
    assert points[0].temperature_c > 0
