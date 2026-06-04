"""MI pipeline stub — load registry and list required agents (E-02-S07)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.services.registry.service import RegistryNotFoundError, RegistryService


def load_required_agents(session: Session, commodity_id: str) -> list[str]:
    """
    Stub orchestration entry: load active registry → required agents.
    Full pipeline deferred to E-04.
    """
    service = RegistryService(session)
    try:
        config = service.get_active_config(commodity_id)
    except RegistryNotFoundError:
        return []
    return list(config.required_agents)
