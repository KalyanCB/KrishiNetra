"""Persistence contracts shared across backend modules (E-01-S02)."""

from shared.persistence.contracts import (
    AppendOnlyRepositoryProtocol,
    ImmutableVersionRepositoryProtocol,
    RepositoryProtocol,
)

__all__ = [
    "AppendOnlyRepositoryProtocol",
    "ImmutableVersionRepositoryProtocol",
    "RepositoryProtocol",
]
