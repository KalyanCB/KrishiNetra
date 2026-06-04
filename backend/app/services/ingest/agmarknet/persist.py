"""Append-only persistence for mapped Agmarknet observation drafts."""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    PriceObservationModel,
)
from backend.app.persistence.repositories.observation import (
    ArrivalObservationRepository,
    PriceObservationRepository,
)
from backend.app.services.ingest.agmarknet.mapper import (
    ArrivalObservationDraft,
    PriceObservationDraft,
)


def persist_price_drafts(
    session: Session,
    drafts: list[PriceObservationDraft],
) -> int:
    """Insert price drafts via append-only repository."""
    if not drafts:
        return 0
    repo = PriceObservationRepository(session)
    for draft in drafts:
        repo.insert_observation(_price_model_from_draft(draft))
    return len(drafts)


def persist_arrival_drafts(
    session: Session,
    drafts: list[ArrivalObservationDraft],
) -> int:
    """Insert arrival drafts via append-only repository."""
    if not drafts:
        return 0
    repo = ArrivalObservationRepository(session)
    for draft in drafts:
        repo.insert_observation(_arrival_model_from_draft(draft))
    return len(drafts)


def _price_model_from_draft(draft: PriceObservationDraft) -> PriceObservationModel:
    return PriceObservationModel(
        observation_id=uuid4(),
        market_id=draft.market_id,
        commodity_id=draft.commodity_id,
        price_type=draft.price_type,
        value=draft.value,
        unit=draft.unit,
        currency=draft.currency,
        observed_at=draft.observed_at,
        as_of_date=draft.as_of_date,
        source=draft.source,
        quality_grade=draft.quality_grade,
        validation_status=draft.validation_status,
    )


def _arrival_model_from_draft(
    draft: ArrivalObservationDraft,
) -> ArrivalObservationModel:
    return ArrivalObservationModel(
        observation_id=uuid4(),
        market_id=draft.market_id,
        commodity_id=draft.commodity_id,
        volume=draft.volume,
        unit=draft.unit,
        observed_at=draft.observed_at,
        as_of_date=draft.as_of_date,
        source=draft.source,
        validation_status=draft.validation_status,
    )
