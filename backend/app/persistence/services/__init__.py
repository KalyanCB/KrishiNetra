"""Persistence services (E-01-S10+)."""

from backend.app.services.registry import (
    RegistryNotFoundError,
    RegistryService,
)

__all__ = ["RegistryNotFoundError", "RegistryService"]
