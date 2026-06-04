"""Persist Agmarknet fixture drafts via observation repositories (PI5 Track C)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    PriceObservationModel,
)
from backend.app.persistence.models.reference import CommodityModel, MarketModel
from backend.app.persistence.repositories.observation import (
    ArrivalObservationRepository,
    PriceObservationRepository,
)
from backend.app.persistence.seeds.runner import SeedRunner
from backend.app.services.ingest.agmarknet.mapper import (
    AgmarknetMapper,
    ArrivalObservationDraft,
    PriceObservationDraft,
)
from backend.app.services.ingest.agmarknet.market_lookup import (
    load_market_lookup_from_seed,
)
from backend.app.services.ingest.agmarknet.parser import parse_ogd_response

DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[4]
    / "tests"
    / "fixtures"
    / "agmarknet"
    / "ogd_cotton_belt_sample.json"
)
COTTON_COMMODITY_ID = "cotton"
SOURCE_AGMARKNET = "agmarknet"


@dataclass(frozen=True, slots=True)
class ObservationCounts:
    """Row counts for cotton Agmarknet population proof."""

    price: int
    arrival: int

    @property
    def total(self) -> int:
        return self.price + self.arrival


@dataclass(frozen=True, slots=True)
class PopulationProofResult:
    """Before/after counts and sample rows from a population run."""

    fixture_path: str
    ogd_record_count: int
    draft_price_count: int
    draft_arrival_count: int
    before: ObservationCounts
    after: ObservationCounts
    inserted: ObservationCounts
    fk_valid: bool
    sample_prices: list[dict[str, object]]
    sample_arrivals: list[dict[str, object]]


def count_cotton_agmarknet(session: Session) -> ObservationCounts:
    """Count persisted cotton rows sourced from Agmarknet."""
    price_n = session.scalar(
        select(func.count())
        .select_from(PriceObservationModel)
        .where(
            PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
            PriceObservationModel.source == SOURCE_AGMARKNET,
        )
    )
    arrival_n = session.scalar(
        select(func.count())
        .select_from(ArrivalObservationModel)
        .where(
            ArrivalObservationModel.commodity_id == COTTON_COMMODITY_ID,
            ArrivalObservationModel.source == SOURCE_AGMARKNET,
        )
    )
    return ObservationCounts(int(price_n or 0), int(arrival_n or 0))


def load_fixture_drafts(
    fixture_path: Path | None = None,
) -> tuple[int, list[PriceObservationDraft], list[ArrivalObservationDraft]]:
    """Parse OGD fixture and map to observation drafts."""
    path = fixture_path or DEFAULT_FIXTURE
    payload = json.loads(path.read_text(encoding="utf-8"))
    records = parse_ogd_response(payload)
    mapper = AgmarknetMapper(load_market_lookup_from_seed())
    prices, arrivals = mapper.map_records(records)
    return len(records), prices, arrivals


def ensure_cotton_seed(session: Session) -> None:
    """Apply E-02 cotton baseline (idempotent)."""
    SeedRunner(session).apply("cotton")


def persist_drafts(
    session: Session,
    prices: list[PriceObservationDraft],
    arrivals: list[ArrivalObservationDraft],
) -> ObservationCounts:
    """Insert mapped drafts via append-only observation repositories."""
    price_repo = PriceObservationRepository(session)
    arrival_repo = ArrivalObservationRepository(session)
    for price_draft in prices:
        price_repo.insert_observation(_price_model_from_draft(price_draft))
    for arrival_draft in arrivals:
        arrival_repo.insert_observation(_arrival_model_from_draft(arrival_draft))
    session.flush()
    return ObservationCounts(len(prices), len(arrivals))


def validate_fk_references(session: Session, market_ids: set[str]) -> bool:
    """Confirm commodity and all referenced markets exist (FK proof)."""
    commodity = session.get(CommodityModel, COTTON_COMMODITY_ID)
    if commodity is None:
        return False
    for market_id in market_ids:
        if session.get(MarketModel, market_id) is None:
            return False
    return True


def run_population_proof(
    session: Session,
    *,
    fixture_path: Path | None = None,
    apply_seed: bool = True,
) -> PopulationProofResult:
    """Seed cotton, persist fixture drafts, and return proof metadata."""
    if apply_seed:
        ensure_cotton_seed(session)
        session.flush()

    before = count_cotton_agmarknet(session)
    ogd_count, prices, arrivals = load_fixture_drafts(fixture_path)
    inserted = persist_drafts(session, prices, arrivals)
    session.commit()
    after = count_cotton_agmarknet(session)

    market_ids = {p.market_id for p in prices} | {a.market_id for a in arrivals}
    fk_valid = validate_fk_references(session, market_ids)

    sample_prices = [_price_row_dict(row) for row in _sample_price_rows(session)]
    sample_arrivals = [_arrival_row_dict(row) for row in _sample_arrival_rows(session)]

    return PopulationProofResult(
        fixture_path=str(fixture_path or DEFAULT_FIXTURE),
        ogd_record_count=ogd_count,
        draft_price_count=len(prices),
        draft_arrival_count=len(arrivals),
        before=before,
        after=after,
        inserted=inserted,
        fk_valid=fk_valid,
        sample_prices=sample_prices,
        sample_arrivals=sample_arrivals,
    )


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


def _arrival_model_from_draft(draft: ArrivalObservationDraft) -> ArrivalObservationModel:
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


def _sample_price_rows(session: Session, *, limit: int = 5) -> list[PriceObservationModel]:
    stmt = (
        select(PriceObservationModel)
        .where(
            PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
            PriceObservationModel.source == SOURCE_AGMARKNET,
        )
        .order_by(
            PriceObservationModel.as_of_date,
            PriceObservationModel.market_id,
            PriceObservationModel.price_type,
        )
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def _sample_arrival_rows(session: Session, *, limit: int = 3) -> list[ArrivalObservationModel]:
    stmt = (
        select(ArrivalObservationModel)
        .where(
            ArrivalObservationModel.commodity_id == COTTON_COMMODITY_ID,
            ArrivalObservationModel.source == SOURCE_AGMARKNET,
        )
        .order_by(ArrivalObservationModel.as_of_date, ArrivalObservationModel.market_id)
        .limit(limit)
    )
    return list(session.scalars(stmt).all())


def _price_row_dict(row: PriceObservationModel) -> dict[str, object]:
    return {
        "observation_id": str(row.observation_id),
        "market_id": row.market_id,
        "commodity_id": row.commodity_id,
        "as_of_date": row.as_of_date.isoformat(),
        "price_type": row.price_type,
        "value": str(row.value),
        "unit": row.unit,
        "currency": row.currency,
        "source": row.source,
        "validation_status": row.validation_status,
        "quality_grade": row.quality_grade,
    }


def _arrival_row_dict(row: ArrivalObservationModel) -> dict[str, object]:
    return {
        "observation_id": str(row.observation_id),
        "market_id": row.market_id,
        "commodity_id": row.commodity_id,
        "as_of_date": row.as_of_date.isoformat(),
        "volume": str(row.volume),
        "unit": row.unit,
        "source": row.source,
        "validation_status": row.validation_status,
    }


def delete_cotton_agmarknet_observations(session: Session) -> ObservationCounts:
    """Remove cotton Agmarknet rows (test/report cleanup only)."""
    import os

    if os.environ.get("KRISHI_PRESERVE_INTEGRATION_CORPUS"):
        return ObservationCounts(0, 0)

    deleted_prices = 0
    deleted_arrivals = 0
    for price_row in session.scalars(
        select(PriceObservationModel).where(
            PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
            PriceObservationModel.source == SOURCE_AGMARKNET,
        )
    ):
        session.delete(price_row)
        deleted_prices += 1
    for arrival_row in session.scalars(
        select(ArrivalObservationModel).where(
            ArrivalObservationModel.commodity_id == COTTON_COMMODITY_ID,
            ArrivalObservationModel.source == SOURCE_AGMARKNET,
        )
    ):
        session.delete(arrival_row)
        deleted_arrivals += 1
    session.commit()
    return ObservationCounts(deleted_prices, deleted_arrivals)
