"""E-01-S02: session factory and Unit of Work."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from backend.app.persistence.dependencies import get_db
from backend.app.persistence.unit_of_work import UnitOfWork


def test_get_db_yields_and_closes_session() -> None:
    gen = get_db()
    session = next(gen)
    assert isinstance(session, Session)
    mock_close = MagicMock()
    session.close = mock_close  # type: ignore[method-assign]
    with pytest.raises(StopIteration):
        next(gen)
    mock_close.assert_called_once()


def test_unit_of_work_commit_on_success() -> None:
    session = MagicMock(spec=Session)
    with UnitOfWork(session=session) as _uow:
        pass
    session.commit.assert_called_once()
    session.rollback.assert_not_called()


def test_unit_of_work_rollback_on_error() -> None:
    session = MagicMock(spec=Session)
    with pytest.raises(RuntimeError), UnitOfWork(session=session):
        raise RuntimeError("boom")
    session.rollback.assert_called_once()
    session.commit.assert_not_called()
