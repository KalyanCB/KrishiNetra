"""Reference entity repositories — stub for E-01-S03 (E-01-S02 pattern)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.persistence.models.reference import CommodityModel
from backend.app.persistence.repositories.base import BaseRepository


class CommodityRepository(BaseRepository[CommodityModel]):
    """Commodity root entity repository."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, CommodityModel)
