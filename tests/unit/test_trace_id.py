"""E-00-S07: trace_id middleware tests."""

from __future__ import annotations

import logging
import uuid

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.middleware.trace_id import TRACE_HEADER

client = TestClient(app)


def test_trace_id_generated() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    trace_id = response.headers.get(TRACE_HEADER)
    assert trace_id is not None
    uuid.UUID(trace_id)


def test_trace_id_preserved() -> None:
    expected = "test-trace-abc-12345"
    response = client.get("/health", headers={TRACE_HEADER: expected})
    assert response.status_code == 200
    assert response.headers.get(TRACE_HEADER) == expected


def test_structured_log_contains_trace_id(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    client.get("/health")
    assert any(getattr(record, "trace_id", None) for record in caplog.records)
