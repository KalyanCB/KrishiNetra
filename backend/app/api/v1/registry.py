"""Commodity Registry API — TDS-010 §10 (E-02-S05/S06)."""

from __future__ import annotations

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from sqlalchemy.orm import Session

from backend.app.config.settings import get_settings
from backend.app.persistence.dependencies import get_db
from backend.app.persistence.models.reference import (
    CommodityModel,
    CommodityProfileModel,
)
from backend.app.persistence.repositories.reference import CommodityRepository
from backend.app.persistence.validation.registry import RegistryValidationError
from backend.app.services.registry.schemas import (
    ActiveRegistryPublicResponse,
    CommodityListItem,
    CommodityListResponse,
    DecisionRulesPublic,
    RegistryActivateResponse,
    RegistryVersionCreateRequest,
    RegistryVersionCreateResponse,
    ValidationErrorDetail,
)
from backend.app.services.registry.service import RegistryNotFoundError, RegistryService

router = APIRouter(tags=["registry"])
internal_router = APIRouter(prefix="/internal/registry", tags=["registry-internal"])

REGISTRY_CACHE_MAX_AGE = 300

DbDep = Annotated[Session, Depends(get_db)]


def _require_ops_api_key(
    x_api_key: Annotated[str | None, Header(alias="X-API-Key")] = None,
) -> None:
    settings = get_settings()
    if not settings.ops_api_key:
        raise HTTPException(status_code=503, detail="Ops API key not configured")
    if x_api_key != settings.ops_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@router.get("/commodities", response_model=CommodityListResponse)
async def list_commodities(
    db: DbDep,
) -> CommodityListResponse:
    """List active commodities with profile metadata (TDS-010 §10.1)."""
    repo = CommodityRepository(db)
    commodities = repo.list_active()
    items: list[CommodityListItem] = []
    for commodity in commodities:
        profile = db.get(CommodityProfileModel, commodity.commodity_id)
        if profile is None:
            continue
        items.append(
            CommodityListItem(
                commodity_id=commodity.commodity_id,
                display_name=profile.display_name,
                status=commodity.status,
                participant_roles_enabled=list(profile.participant_roles_enabled or []),
                phase_1_active_roles=list(profile.phase_1_active_roles or []),
            )
        )
    return CommodityListResponse(commodities=items)


@router.get(
    "/commodities/{commodity_id}/registry/active",
    response_model=ActiveRegistryPublicResponse,
)
async def get_active_registry_public(
    commodity_id: str,
    response: Response,
    db: DbDep,
) -> ActiveRegistryPublicResponse:
    """Public read subset of active registry (TDS-010 §10.2)."""
    if db.get(CommodityModel, commodity_id) is None:
        raise HTTPException(status_code=404, detail="Commodity not found")

    service = RegistryService(db)
    try:
        registry = service.get_active_config(commodity_id)
    except RegistryNotFoundError as exc:
        raise HTTPException(status_code=404, detail="No active registry") from exc

    response.headers["Cache-Control"] = f"public, max-age={REGISTRY_CACHE_MAX_AGE}"

    rules = registry.decision_rules
    return ActiveRegistryPublicResponse(
        registry_id=registry.registry_id,
        version=registry.version,
        effective_from=registry.effective_from,
        required_agents=list(registry.required_agents),
        optional_agents=list(registry.optional_agents or []),
        forecast_horizons=list(registry.forecast_horizons),
        decision_rules_public=DecisionRulesPublic(
            msp_proximity_pct=float(rules["msp_proximity_pct"]),
            default_partial_sell_pct=float(rules["default_partial_sell_pct"]),
        ),
    )


@internal_router.post(
    "/versions",
    response_model=RegistryVersionCreateResponse,
    dependencies=[Depends(_require_ops_api_key)],
)
async def create_registry_version(
    payload: RegistryVersionCreateRequest,
    db: DbDep,
) -> RegistryVersionCreateResponse:
    """Create inactive registry version (TDS-010 §10.3)."""
    if db.get(CommodityModel, payload.commodity_id) is None:
        raise HTTPException(status_code=404, detail="Commodity not found")

    service = RegistryService(db)
    try:
        created = service.create_registry_version(
            payload.commodity_id,
            payload.model_dump(),
        )
        db.commit()
    except RegistryValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=ValidationErrorDetail(
                detail="Registry validation failed",
                errors=[str(exc)],
            ).model_dump(),
        ) from exc

    return RegistryVersionCreateResponse(
        registry_id=created.registry_id,
        commodity_id=created.commodity_id,
        version=created.version,
        is_active=created.is_active,
    )


@internal_router.post(
    "/versions/{registry_id}/activate",
    response_model=RegistryActivateResponse,
    dependencies=[Depends(_require_ops_api_key)],
)
async def activate_registry_version(
    registry_id: UUID,
    db: DbDep,
) -> RegistryActivateResponse:
    """Activate registry version; deactivates prior active (ADR-003)."""
    service = RegistryService(db)
    target = service.get_registry_by_id(registry_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Registry version not found")

    try:
        activated = service.activate_registry_version(
            registry_id,
            effective_to_for_prior=date.today(),
        )
        db.commit()
    except RegistryValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=ValidationErrorDetail(
                detail="Registry validation failed",
                errors=[str(exc)],
            ).model_dump(),
        ) from exc

    return RegistryActivateResponse(
        registry_id=activated.registry_id,
        commodity_id=activated.commodity_id,
        version=activated.version,
        is_active=activated.is_active,
        effective_from=activated.effective_from,
    )
