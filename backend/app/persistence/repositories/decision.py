"""Decision session stack repositories — E-01-S07."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.decision import (
    DecisionSessionModel,
    OutcomeModel,
    RecommendationModel,
    RecommendationVersionModel,
    UserContextModel,
)
from backend.app.persistence.repositories.base import (
    BaseRepository,
    ImmutableVersionRepository,
)
from backend.app.persistence.validation.decision import (
    validate_persona_type,
    validate_recommendation_version_fields,
    validate_user_context_fields,
)


class UserContextRepository(BaseRepository[UserContextModel]):
    """Insert-only user context rows."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, UserContextModel)

    def insert_context(self, entity: UserContextModel) -> UserContextModel:
        validate_user_context_fields(
            persona_type=entity.persona_type,
            liquidity_need=entity.liquidity_need,
        )
        return self.insert(entity)


class DecisionSessionRepository(BaseRepository[DecisionSessionModel]):
    """Decision session audit root — metadata updates allowed for linkage fields."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, DecisionSessionModel)

    def insert_session(self, entity: DecisionSessionModel) -> DecisionSessionModel:
        validate_persona_type(entity.persona_type)
        return self.insert(entity)

    def get_session(
        self, session_id: UUID, *, created_at: datetime | None = None
    ) -> DecisionSessionModel | None:
        if created_at is None:
            stmt = select(DecisionSessionModel).where(
                DecisionSessionModel.session_id == session_id
            )
            return self._session.scalars(stmt).first()
        return self._session.get(self._model, (session_id, created_at))

    def link_recommendation(
        self,
        session: DecisionSessionModel,
        recommendation_id: UUID,
    ) -> DecisionSessionModel:
        session.recommendation_id = recommendation_id
        self._session.flush()
        return session


class RecommendationRepository(BaseRepository[RecommendationModel]):
    """Session-scoped recommendation logical identity."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, RecommendationModel)

    def insert_recommendation(
        self, entity: RecommendationModel
    ) -> RecommendationModel:
        return self.insert(entity)

    def get_by_session_id(self, session_id: UUID) -> RecommendationModel | None:
        stmt = select(RecommendationModel).where(
            RecommendationModel.session_id == session_id
        )
        return self._session.scalars(stmt).first()


class RecommendationVersionRepository(
    ImmutableVersionRepository[RecommendationVersionModel]
):
    """Insert-only recommendation versions; UPDATE blocked at repository layer."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, RecommendationVersionModel)

    def insert_version(
        self, entity: RecommendationVersionModel
    ) -> RecommendationVersionModel:
        validate_recommendation_version_fields(
            action_type=entity.action_type,
            recommendation_confidence=entity.recommendation_confidence,
        )
        return self.insert(entity)


class OutcomeRepository(BaseRepository[OutcomeModel]):
    """Outcome capture — one row per session enforced by UNIQUE constraint."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, OutcomeModel)

    def insert_outcome(self, entity: OutcomeModel) -> OutcomeModel:
        return self.insert(entity)
