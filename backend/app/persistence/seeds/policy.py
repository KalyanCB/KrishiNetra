"""Policy observation seed — idempotent cotton policy stubs (PI10 Track B)."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import ObservationValidationStatus
from backend.app.persistence.models.policy import PolicyObservationModel
from backend.app.persistence.repositories.policy import PolicyObservationRepository

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_policy_fixture(name: str) -> dict[str, Any]:
    path = FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        msg = f"Policy fixture not found: {path}"
        raise FileNotFoundError(msg)
    with path.open(encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


def _business_key(row: dict[str, Any], *, commodity_id: str) -> tuple[str, ...]:
    return (
        commodity_id,
        row["policy_type"],
        row["source"],
        row["published_date"],
        row.get("summary", ""),
    )


class PolicySeedRunner:
    """Apply policy fixture rows; skip duplicates by business key."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = PolicyObservationRepository(session)

    def apply(self, fixture_name: str) -> int:
        """Insert missing policy rows; return count inserted."""
        data = load_policy_fixture(fixture_name)
        commodity_id = data["commodity_id"]
        inserted = 0
        for row in data.get("observations", []):
            if self._exists(commodity_id, row):
                continue
            entity = PolicyObservationModel(
                observation_id=uuid4(),
                commodity_id=commodity_id,
                policy_type=row["policy_type"],
                source=row["source"],
                published_date=date.fromisoformat(row["published_date"]),
                effective_date=date.fromisoformat(row["effective_date"]),
                impact_direction=row["impact_direction"],
                confidence=Decimal(row["confidence"]),
                summary=row.get("summary"),
                provenance=row.get("provenance", {}),
                validation_status=ObservationValidationStatus.VALIDATED.value,
            )
            self._repo.insert_observation(entity)
            inserted += 1
        return inserted

    def _exists(self, commodity_id: str, row: dict[str, Any]) -> bool:
        key = _business_key(row, commodity_id=commodity_id)
        stmt = select(PolicyObservationModel).where(
            PolicyObservationModel.commodity_id == commodity_id,
            PolicyObservationModel.policy_type == row["policy_type"],
            PolicyObservationModel.source == row["source"],
            PolicyObservationModel.published_date
            == date.fromisoformat(row["published_date"]),
        )
        for existing in self._session.scalars(stmt).all():
            if (
                _business_key(
                    {
                        "policy_type": existing.policy_type,
                        "source": existing.source,
                        "published_date": existing.published_date.isoformat(),
                        "summary": existing.summary or "",
                    },
                    commodity_id=commodity_id,
                )
                == key
            ):
                return True
        return False
