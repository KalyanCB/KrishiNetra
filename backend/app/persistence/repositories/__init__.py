"""Persistence repositories (E-01-S02+)."""

from backend.app.persistence.repositories.base import (
    BaseRepository,
    ImmutableVersionRepository,
)
from backend.app.persistence.repositories.forecast import (
    FeatureSetRepository,
    FeatureVectorRepository,
    ForecastRepository,
    ForecastVersionRepository,
)
from backend.app.persistence.repositories.observation import (
    ArrivalObservationRepository,
    PriceObservationRepository,
)
from backend.app.persistence.repositories.quality import DataQualitySnapshotRepository
from backend.app.persistence.repositories.reference import CommodityRepository
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.repositories.signal import (
    SignalSnapshotRepository,
    StructuredSignalRepository,
)

__all__ = [
    "FeatureSetRepository",
    "FeatureVectorRepository",
    "ForecastRepository",
    "ForecastVersionRepository",
    "ArrivalObservationRepository",
    "BaseRepository",
    "CommodityRegistryRepository",
    "CommodityRepository",
    "DataQualitySnapshotRepository",
    "ImmutableVersionRepository",
    "PriceObservationRepository",
    "SignalSnapshotRepository",
    "StructuredSignalRepository",
]
