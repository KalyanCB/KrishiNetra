"""Registry API schemas — TDS-010 §10."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CommodityListItem(BaseModel):
    commodity_id: str
    display_name: str
    status: str
    participant_roles_enabled: list[str]
    phase_1_active_roles: list[str]


class CommodityListResponse(BaseModel):
    commodities: list[CommodityListItem]


class DecisionRulesPublic(BaseModel):
    msp_proximity_pct: float
    default_partial_sell_pct: float


class ActiveRegistryPublicResponse(BaseModel):
    registry_id: UUID
    version: str
    effective_from: date
    required_agents: list[str]
    optional_agents: list[str]
    forecast_horizons: list[int]
    decision_rules_public: DecisionRulesPublic


class RegistryVersionCreateRequest(BaseModel):
    commodity_id: str
    version: str
    effective_from: date
    required_agents: list[str]
    optional_agents: list[str] | None = None
    signal_weights: dict[str, float] | None = None
    regime_priority: list[str] | None = None
    forecast_horizons: list[int] = Field(default_factory=lambda: [30, 60, 90])
    decision_rules: dict[str, Any]
    price_sources: list[str] | None = None
    arrival_sources: list[str] | None = None
    demand_drivers: list[str] | None = None
    policy_drivers: list[str] | None = None
    weather_variables: list[str] | None = None


class RegistryVersionCreateResponse(BaseModel):
    registry_id: UUID
    commodity_id: str
    version: str
    is_active: bool


class RegistryActivateResponse(BaseModel):
    registry_id: UUID
    commodity_id: str
    version: str
    is_active: bool
    effective_from: date


class ValidationErrorDetail(BaseModel):
    detail: str
    errors: list[str] = Field(default_factory=list)
