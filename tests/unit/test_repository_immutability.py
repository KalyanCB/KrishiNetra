"""E-01-S02: test_repository_insert_only_forecast_version (stub model)."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from backend.app.persistence.repositories.base import ImmutableVersionRepository
from shared.persistence.contracts import ImmutableVersionUpdateError


class _StubBase(DeclarativeBase):
    pass


class _StubForecastVersion(_StubBase):
    """Minimal stand-in for ForecastVersion until E-01-S06."""

    __tablename__ = "stub_forecast_version"

    forecast_version_id: Mapped[str] = mapped_column(primary_key=True)
    point_forecast: Mapped[float] = mapped_column()


def test_repository_insert_only_forecast_version() -> None:
    session = MagicMock(spec=Session)
    repo = ImmutableVersionRepository(session, _StubForecastVersion)
    row = _StubForecastVersion(forecast_version_id=str(uuid4()), point_forecast=100.0)
    inserted = repo.insert(row)
    session.add.assert_called_once_with(row)
    session.flush.assert_called_once()
    assert inserted.point_forecast == 100.0
    with pytest.raises(ImmutableVersionUpdateError):
        repo.update(inserted)
