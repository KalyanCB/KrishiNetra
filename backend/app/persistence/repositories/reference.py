"""Reference entity repositories — E-01-S03, E-02-S01."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.reference import (
    CommodityModel,
    CommodityProfileModel,
    MarketModel,
    RegionModel,
)
from backend.app.persistence.repositories.base import BaseRepository


class CommodityRepository(BaseRepository[CommodityModel]):
    """Commodity root entity repository."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, CommodityModel)

    def get_with_profile(self, commodity_id: str) -> CommodityModel | None:
        return self._session.get(CommodityModel, commodity_id)

    def list_active(self) -> list[CommodityModel]:
        stmt = (
            select(CommodityModel)
            .where(CommodityModel.status == "active")
            .order_by(CommodityModel.commodity_id)
        )
        return list(self._session.scalars(stmt).all())

    def upsert_commodity(self, entity: CommodityModel) -> CommodityModel:
        existing = self.get_by_id(entity.commodity_id)
        if existing is None:
            return self.insert(entity)
        existing.name = entity.name
        existing.status = entity.status
        existing.reference_implementation_flag = entity.reference_implementation_flag
        self._session.flush()
        return existing


class CommodityProfileRepository(BaseRepository[CommodityProfileModel]):
    """Commodity profile repository."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, CommodityProfileModel)

    def upsert_profile(self, entity: CommodityProfileModel) -> CommodityProfileModel:
        existing = self.get_by_id(entity.commodity_id)
        if existing is None:
            return self.insert(entity)
        existing.display_name = entity.display_name
        existing.unit = entity.unit
        existing.currency = entity.currency
        existing.quality_dimensions = entity.quality_dimensions
        existing.storage_characteristics = entity.storage_characteristics
        existing.participant_roles_enabled = entity.participant_roles_enabled
        existing.phase_1_active_roles = entity.phase_1_active_roles
        self._session.flush()
        return existing


class RegionRepository(BaseRepository[RegionModel]):
    """Region hierarchy repository."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, RegionModel)

    def upsert_region(self, entity: RegionModel) -> RegionModel:
        existing = self.get_by_id(entity.region_id)
        if existing is None:
            return self.insert(entity)
        existing.name = entity.name
        existing.type = entity.type
        existing.parent_region_id = entity.parent_region_id
        existing.external_refs = entity.external_refs
        self._session.flush()
        return existing


class MarketRepository(BaseRepository[MarketModel]):
    """Market repository."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, MarketModel)

    def upsert_market(self, entity: MarketModel) -> MarketModel:
        existing = self.get_by_id(entity.market_id)
        if existing is None:
            return self.insert(entity)
        existing.region_id = entity.region_id
        existing.market_type = entity.market_type
        existing.name = entity.name
        existing.source_identifiers = entity.source_identifiers
        self._session.flush()
        return existing
