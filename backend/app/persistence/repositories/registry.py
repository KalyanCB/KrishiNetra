"""CommodityRegistry repository — versioned config (E-01-S10, ADR-003)."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.repositories.base import BaseRepository
from backend.app.persistence.validation.registry import validate_registry_config


class CommodityRegistryRepository(BaseRepository[CommodityRegistryModel]):
    """Versioned config: insert new versions; activate via swap (ADR-003)."""

    def __init__(self, session: Session) -> None:
        super().__init__(session, CommodityRegistryModel)

    def get_registry(self, registry_id: UUID) -> CommodityRegistryModel | None:
        return self._session.get(self._model, registry_id)

    def get_active(self, commodity_id: str) -> CommodityRegistryModel | None:
        stmt = select(CommodityRegistryModel).where(
            CommodityRegistryModel.commodity_id == commodity_id,
            CommodityRegistryModel.is_active.is_(True),
        )
        return self._session.scalars(stmt).first()

    def insert_version(self, entity: CommodityRegistryModel) -> CommodityRegistryModel:
        validate_registry_config(
            required_agents=entity.required_agents,
            optional_agents=entity.optional_agents,
            decision_rules=entity.decision_rules,
        )
        return self.insert(entity)

    def activate_version(
        self,
        registry_id: UUID,
        *,
        effective_to_for_prior: date | None = None,
    ) -> CommodityRegistryModel:
        """
        Swap active flag in a single transaction (ADR-003 §2.3).
        Deactivates prior active row and sets effective_to when provided.
        """
        target = self.get_registry(registry_id)
        if target is None:
            raise ValueError(f"registry not found: {registry_id}")

        validate_registry_config(
            required_agents=target.required_agents,
            optional_agents=target.optional_agents,
            decision_rules=target.decision_rules,
        )

        prior = self.get_active(target.commodity_id)
        if prior is not None and prior.registry_id != registry_id:
            prior.is_active = False
            if effective_to_for_prior is not None:
                prior.effective_to = effective_to_for_prior

        target.is_active = True
        target.effective_to = None
        self._session.flush()
        return target
