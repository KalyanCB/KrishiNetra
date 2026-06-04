"""RegistryService re-export — prefer backend.app.services.registry for E-03/E-04."""

from backend.app.services.registry.service import (
    RegistryNotFoundError,
    RegistryService,
)

__all__ = ["RegistryNotFoundError", "RegistryService"]
