"""Append-only policy observation repository — PI10 Track B."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.policy import PolicyObservationModel
from backend.app.persistence.repositories.base import BaseRepository
from backend.app.persistence.validation.policy import (
    validate_policy_confidence,
    validate_policy_impact_direction,
    validate_policy_source,
    validate_policy_type,
    validate_validation_status,
)


class PolicyObservationRepository(BaseRepository[PolicyObservationModel]):
    """Append-only policy events; corrections via new row + supersedes_id."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, PolicyObservationModel)

    def insert_observation(
        self, entity: PolicyObservationModel
    ) -> PolicyObservationModel:
        validate_policy_type(entity.policy_type)
        validate_policy_source(entity.source)
        validate_policy_impact_direction(entity.impact_direction)
        validate_policy_confidence(entity.confidence)
        validate_validation_status(entity.validation_status)
        return self.insert(entity)

    def get_observation(self, observation_id: UUID) -> PolicyObservationModel | None:
        return self._session.get(self._model, observation_id)

    def list_by_commodity_date_range(
        self,
        commodity_id: str,
        start: date,
        end: date,
        *,
        policy_type: str | None = None,
    ) -> list[PolicyObservationModel]:
        stmt = select(PolicyObservationModel).where(
            PolicyObservationModel.commodity_id == commodity_id,
            PolicyObservationModel.effective_date >= start,
            PolicyObservationModel.effective_date <= end,
        )
        if policy_type is not None:
            stmt = stmt.where(PolicyObservationModel.policy_type == policy_type)
        stmt = stmt.order_by(PolicyObservationModel.effective_date.desc())
        return list(self._session.scalars(stmt).all())
