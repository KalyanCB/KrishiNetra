"""RegistryService — ADR-003 read pattern for downstream pipelines."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.repositories.registry import CommodityRegistryRepository


class RegistryNotFoundError(LookupError):
    """No active registry exists for the commodity."""


class RegistryService:
    """Downstream pipelines read config only via get_active_config (ADR-003)."""

    def __init__(self, session: Session) -> None:
        self._repo = CommodityRegistryRepository(session)

    def get_active_config(self, commodity_id: str) -> CommodityRegistryModel:
        config = self._repo.get_active(commodity_id)
        if config is None:
            raise RegistryNotFoundError(
                f"no active commodity_registry for commodity_id={commodity_id}"
            )
        return config
