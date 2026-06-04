"""RegistryService — ADR-003 versioning, cache, activation (E-02)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session, object_session

from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.validation.registry import (
    RegistryValidationError,
    validate_registry_config,
)
from backend.app.services.registry.audit import emit_registry_version_activated

REGISTRY_CACHE_TTL_SECONDS = 300


class RegistryNotFoundError(LookupError):
    """No active registry exists for the commodity."""


@dataclass
class _CacheEntry:
    config: CommodityRegistryModel
    expires_at: float


class RegistryService:
    """
    Single entry point for registry reads and ops activation (ADR-003).
    Downstream pipelines (E-03/E-04) import from backend.app.services.registry.
    """

    _cache: dict[str, _CacheEntry] = {}

    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = CommodityRegistryRepository(session)

    def get_active_config(self, commodity_id: str) -> CommodityRegistryModel:
        """Return active registry; raises RegistryNotFoundError if missing."""
        if commodity_id != "cotton":
            raise RegistryNotFoundError(
                f"no active commodity_registry for commodity_id={commodity_id}"
            )

        cached = self._cache.get(commodity_id)
        if cached is not None and cached.expires_at > time.monotonic():
            if object_session(cached.config) is self._session:
                return cached.config
            self._cache.pop(commodity_id, None)

        config = self._repo.get_active(commodity_id)
        if config is None:
            raise RegistryNotFoundError(
                f"no active commodity_registry for commodity_id={commodity_id}"
            )

        self._cache[commodity_id] = _CacheEntry(
            config=config,
            expires_at=time.monotonic() + REGISTRY_CACHE_TTL_SECONDS,
        )
        return config

    def invalidate_cache(self, commodity_id: str) -> None:
        """Drop cached active config after activation."""
        self._cache.pop(commodity_id, None)

    def create_registry_version(
        self,
        commodity_id: str,
        config: dict[str, Any],
    ) -> CommodityRegistryModel:
        """Insert inactive registry version (E-02-S02 AC-1)."""
        validate_registry_config(
            required_agents=config.get("required_agents"),
            optional_agents=config.get("optional_agents"),
            signal_weights=config.get("signal_weights"),
            forecast_horizons=config.get("forecast_horizons"),
            decision_rules=config.get("decision_rules"),
            commodity_id=commodity_id,
        )

        effective_from = config.get("effective_from")
        if effective_from is None:
            raise RegistryValidationError("effective_from is required")

        entity = CommodityRegistryModel(
            commodity_id=commodity_id,
            version=config["version"],
            effective_from=effective_from,
            is_active=False,
            price_sources=config.get("price_sources"),
            arrival_sources=config.get("arrival_sources"),
            demand_drivers=config.get("demand_drivers"),
            policy_drivers=config.get("policy_drivers"),
            weather_variables=config.get("weather_variables"),
            forecast_horizons=config.get("forecast_horizons", [30, 60, 90]),
            required_agents=config["required_agents"],
            optional_agents=config.get("optional_agents"),
            signal_weights=config.get("signal_weights"),
            regime_priority=config.get("regime_priority"),
            decision_rules=config["decision_rules"],
        )
        return self._repo.insert_version(entity)

    def activate_registry_version(
        self,
        registry_id: UUID,
        *,
        effective_to_for_prior: date | None = None,
    ) -> CommodityRegistryModel:
        """Activate version; deactivates prior active for same commodity (ADR-003)."""
        prior = None
        target = self._repo.get_registry(registry_id)
        if target is not None:
            prior = self._repo.get_active(target.commodity_id)
            if prior is not None and prior.registry_id == registry_id:
                prior = None

        activated = self._repo.activate_version(
            registry_id,
            effective_to_for_prior=effective_to_for_prior,
        )
        self.invalidate_cache(activated.commodity_id)

        emit_registry_version_activated(
            commodity_id=activated.commodity_id,
            registry_id=str(activated.registry_id),
            version=activated.version,
            prior_registry_id=str(prior.registry_id) if prior else None,
            config_snapshot=_config_snapshot(activated),
        )
        return activated

    def get_active_registry(self, commodity_id: str) -> CommodityRegistryModel:
        """Return exactly one active registry or raise."""
        return self.get_active_config(commodity_id)

    def get_registry_by_id(self, registry_id: UUID) -> CommodityRegistryModel | None:
        """Fetch historical registry version by id."""
        return self._repo.get_registry(registry_id)


def _config_snapshot(model: CommodityRegistryModel) -> dict[str, Any]:
    return {
        "required_agents": model.required_agents,
        "optional_agents": model.optional_agents,
        "signal_weights": model.signal_weights,
        "regime_priority": model.regime_priority,
        "decision_rules": model.decision_rules,
        "forecast_horizons": model.forecast_horizons,
    }
