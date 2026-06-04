"""Seed runner — idempotent cotton baseline (E-02-S01/S04)."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.persistence.models.reference import (
    CommodityModel,
    CommodityProfileModel,
    CommodityStatus,
    MarketModel,
    RegionModel,
)
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.repositories.reference import (
    CommodityProfileRepository,
    CommodityRepository,
    MarketRepository,
    RegionRepository,
)
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.services.registry.service import RegistryService

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    """Load a JSON fixture from seeds/fixtures/."""
    path = FIXTURES_DIR / f"{name}.json"
    if not path.exists():
        msg = f"Fixture not found: {path}"
        raise FileNotFoundError(msg)
    with path.open(encoding="utf-8") as handle:
        return cast(dict[str, Any], json.load(handle))


class SeedRunner:
    """
    Apply reference seed data inside a transaction.
    Idempotent: second run does not duplicate rows (E-02-S01 AC-5).
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._commodities = CommodityRepository(session)
        self._profiles = CommodityProfileRepository(session)
        self._regions = RegionRepository(session)
        self._markets = MarketRepository(session)
        self._registries = CommodityRegistryRepository(session)
        self._registry_service = RegistryService(session)

    def apply(self, fixture_name: str) -> None:
        """Apply fixture rows for the named commodity seed."""
        if fixture_name != "cotton":
            msg = f"Unknown fixture: {fixture_name}"
            raise ValueError(msg)
        data = load_fixture(fixture_name)
        self._apply_cotton(data)

    def _apply_cotton(self, data: dict[str, Any]) -> None:
        commodity_data = data["commodity"]
        commodity_id = commodity_data["commodity_id"]

        self._commodities.upsert_commodity(
            CommodityModel(
                commodity_id=commodity_id,
                name=commodity_data["name"],
                status=commodity_data.get("status", CommodityStatus.ACTIVE.value),
                reference_implementation_flag=commodity_data.get(
                    "reference_implementation_flag", False
                ),
            )
        )

        profile_data = data["commodity_profile"]
        self._profiles.upsert_profile(
            CommodityProfileModel(
                commodity_id=commodity_id,
                display_name=profile_data["display_name"],
                unit=profile_data.get("unit", "quintal"),
                currency=profile_data.get("currency", "INR"),
                quality_dimensions=profile_data.get("quality_dimensions"),
                storage_characteristics=profile_data.get("storage_characteristics"),
                participant_roles_enabled=profile_data.get("participant_roles_enabled"),
                phase_1_active_roles=profile_data.get("phase_1_active_roles"),
            )
        )

        for region_data in data.get("regions", []):
            self._regions.upsert_region(
                RegionModel(
                    region_id=region_data["region_id"],
                    commodity_id=commodity_id,
                    name=region_data["name"],
                    type=region_data["type"],
                    parent_region_id=region_data.get("parent_region_id"),
                    external_refs=region_data.get("external_refs"),
                )
            )

        for market_data in data.get("markets", []):
            self._markets.upsert_market(
                MarketModel(
                    market_id=market_data["market_id"],
                    region_id=market_data["region_id"],
                    commodity_id=commodity_id,
                    market_type=market_data["market_type"],
                    name=market_data["name"],
                    source_identifiers=market_data.get("source_identifiers"),
                )
            )

        self._apply_registry(commodity_id, data["registry"])

    def _apply_registry(self, commodity_id: str, registry_data: dict[str, Any]) -> None:
        version = registry_data["version"]
        stmt = select(CommodityRegistryModel).where(
            CommodityRegistryModel.commodity_id == commodity_id,
            CommodityRegistryModel.version == version,
        )
        existing = self._session.scalars(stmt).first()
        if existing is not None:
            if registry_data.get("is_active") and not existing.is_active:
                self._registry_service.activate_registry_version(
                    existing.registry_id,
                    effective_to_for_prior=date.today(),
                )
            return

        effective_from_raw = registry_data["effective_from"]
        if isinstance(effective_from_raw, str):
            effective_from = date.fromisoformat(effective_from_raw)
        else:
            effective_from = effective_from_raw

        entity = CommodityRegistryModel(
            commodity_id=commodity_id,
            version=version,
            effective_from=effective_from,
            is_active=False,
            price_sources=registry_data.get("price_sources"),
            arrival_sources=registry_data.get("arrival_sources"),
            demand_drivers=registry_data.get("demand_drivers"),
            policy_drivers=registry_data.get("policy_drivers"),
            weather_variables=registry_data.get("weather_variables"),
            forecast_horizons=registry_data.get("forecast_horizons", [30, 60, 90]),
            required_agents=registry_data["required_agents"],
            optional_agents=registry_data.get("optional_agents"),
            signal_weights=registry_data.get("signal_weights"),
            regime_priority=registry_data.get("regime_priority"),
            decision_rules=registry_data["decision_rules"],
        )
        inserted = self._registries.insert_version(entity)

        if registry_data.get("is_active"):
            self._registry_service.activate_registry_version(
                inserted.registry_id,
                effective_to_for_prior=date.today(),
            )
