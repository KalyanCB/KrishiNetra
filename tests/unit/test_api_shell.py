"""E-00-S03: FastAPI application shell smoke tests."""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.main import app
from backend.app.persistence.dependencies import get_db

V1_STUB_ROUTES: list[tuple[str, str]] = [
    ("GET", "/v1/commodities/cotton/market-intelligence"),
    ("POST", "/v1/commodities/cotton/decisions"),
    ("POST", "/v1/decisions/test-session/conversation"),
    ("POST", "/v1/decisions/test-session/outcomes"),
]

V1_IMPLEMENTED_ROUTES: list[tuple[str, str, int]] = [
    ("GET", "/v1/commodities", 200),
]


@pytest.fixture
def client() -> TestClient:
    mock_session = MagicMock(spec=Session)
    mock_session.scalars.return_value.all.return_value = []

    def _override_db() -> Generator[MagicMock, None, None]:
        yield mock_session

    app.dependency_overrides[get_db] = _override_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_health_endpoint(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("method,path", V1_STUB_ROUTES)
def test_v1_mount(client: TestClient, method: str, path: str) -> None:
    response = client.request(method, path)
    assert response.status_code in {404, 501}


@pytest.mark.parametrize("method,path,expected", V1_IMPLEMENTED_ROUTES)
def test_v1_implemented_routes(
    client: TestClient, method: str, path: str, expected: int
) -> None:
    response = client.request(method, path)
    assert response.status_code == expected
