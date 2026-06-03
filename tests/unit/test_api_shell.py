"""E-00-S03: FastAPI application shell smoke tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

V1_STUB_ROUTES: list[tuple[str, str]] = [
    ("GET", "/v1/commodities/cotton/market-intelligence"),
    ("POST", "/v1/commodities/cotton/decisions"),
    ("POST", "/v1/decisions/test-session/conversation"),
    ("POST", "/v1/decisions/test-session/outcomes"),
    ("GET", "/v1/commodities"),
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("method,path", V1_STUB_ROUTES)
def test_v1_mount(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, path)
    assert response.status_code in {404, 501}
