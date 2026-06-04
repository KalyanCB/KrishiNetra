"""Business-key deduplication for Agmarknet observation inserts (E-03-S01)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Generic, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    PriceObservationModel,
)
from backend.app.services.ingest.agmarknet.mapper import (
    ArrivalObservationDraft,
    PriceObservationDraft,
)

PriceBusinessKey = tuple[str, date, str, str, str | None]
ArrivalBusinessKey = tuple[str, date, str, str]

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class DedupeResult(Generic[T]):
    """Drafts split into insert candidates and duplicates."""

    to_insert: list[T]
    skipped: int


def price_business_key(draft: PriceObservationDraft) -> PriceBusinessKey:
    return (
        draft.market_id,
        draft.as_of_date,
        draft.source,
        draft.price_type,
        draft.quality_grade,
    )


def arrival_business_key(draft: ArrivalObservationDraft) -> ArrivalBusinessKey:
    return (
        draft.market_id,
        draft.as_of_date,
        draft.source,
        draft.commodity_id,
    )


def filter_new_price_drafts(
    session: Session,
    drafts: list[PriceObservationDraft],
) -> DedupeResult[PriceObservationDraft]:
    """Return drafts whose business key is not already persisted."""
    if not drafts:
        return DedupeResult([], 0)

    existing = _load_existing_price_keys(session, drafts)
    to_insert: list[PriceObservationDraft] = []
    skipped = 0
    for draft in drafts:
        key = price_business_key(draft)
        if key in existing:
            skipped += 1
            continue
        to_insert.append(draft)
        existing.add(key)
    return DedupeResult(to_insert, skipped)


def filter_new_arrival_drafts(
    session: Session,
    drafts: list[ArrivalObservationDraft],
) -> DedupeResult[ArrivalObservationDraft]:
    """Return arrival drafts not already present for market/date/source/commodity."""
    if not drafts:
        return DedupeResult([], 0)

    existing = _load_existing_arrival_keys(session, drafts)
    to_insert: list[ArrivalObservationDraft] = []
    skipped = 0
    for draft in drafts:
        key = arrival_business_key(draft)
        if key in existing:
            skipped += 1
            continue
        to_insert.append(draft)
        existing.add(key)
    return DedupeResult(to_insert, skipped)


def _load_existing_price_keys(
    session: Session,
    drafts: list[PriceObservationDraft],
) -> set[PriceBusinessKey]:
    dates = {draft.as_of_date for draft in drafts}
    sources = {draft.source for draft in drafts}
    stmt = select(
        PriceObservationModel.market_id,
        PriceObservationModel.as_of_date,
        PriceObservationModel.source,
        PriceObservationModel.price_type,
        PriceObservationModel.quality_grade,
    ).where(
        PriceObservationModel.as_of_date.in_(dates),
        PriceObservationModel.source.in_(sources),
    )
    return {tuple(row) for row in session.execute(stmt).all()}


def _load_existing_arrival_keys(
    session: Session,
    drafts: list[ArrivalObservationDraft],
) -> set[ArrivalBusinessKey]:
    dates = {draft.as_of_date for draft in drafts}
    sources = {draft.source for draft in drafts}
    stmt = select(
        ArrivalObservationModel.market_id,
        ArrivalObservationModel.as_of_date,
        ArrivalObservationModel.source,
        ArrivalObservationModel.commodity_id,
    ).where(
        ArrivalObservationModel.as_of_date.in_(dates),
        ArrivalObservationModel.source.in_(sources),
    )
    return {tuple(row) for row in session.execute(stmt).all()}
