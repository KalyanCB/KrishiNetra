"""Unit of Work transaction boundary (E-01-S02)."""

from __future__ import annotations

from types import TracebackType

from sqlalchemy.orm import Session

from backend.app.persistence.database import SessionLocal
from backend.app.persistence.repositories.decision import (
    DecisionSessionRepository,
    OutcomeRepository,
    RecommendationRepository,
    RecommendationVersionRepository,
    UserContextRepository,
)
from backend.app.persistence.repositories.forecast import (
    FeatureSetRepository,
    FeatureVectorRepository,
    ForecastFeatureSnapshotRepository,
    ForecastRepository,
    ForecastVersionRepository,
)
from backend.app.persistence.repositories.futures import FuturesObservationRepository
from backend.app.persistence.repositories.observation import (
    ArrivalObservationRepository,
    PriceObservationRepository,
)
from backend.app.persistence.repositories.policy import PolicyObservationRepository
from backend.app.persistence.repositories.quality import DataQualitySnapshotRepository
from backend.app.persistence.repositories.reference import CommodityRepository
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.repositories.signal import (
    SignalSnapshotRepository,
    StructuredSignalRepository,
)
from backend.app.persistence.repositories.weather import WeatherObservationRepository


class UnitOfWork:
    """Coordinates a single transaction across repositories."""

    def __init__(self, session: Session | None = None) -> None:
        self._owns_session = session is None
        self.session = session or SessionLocal()
        self.commodities = CommodityRepository(self.session)
        self.registries = CommodityRegistryRepository(self.session)
        self.quality_snapshots = DataQualitySnapshotRepository(self.session)
        self.price_observations = PriceObservationRepository(self.session)
        self.arrival_observations = ArrivalObservationRepository(self.session)
        self.weather_observations = WeatherObservationRepository(self.session)
        self.futures_observations = FuturesObservationRepository(self.session)
        self.policy_observations = PolicyObservationRepository(self.session)
        self.structured_signals = StructuredSignalRepository(self.session)
        self.signal_snapshots = SignalSnapshotRepository(self.session)
        self.forecasts = ForecastRepository(self.session)
        self.forecast_versions = ForecastVersionRepository(self.session)
        self.feature_sets = FeatureSetRepository(self.session)
        self.feature_vectors = FeatureVectorRepository(self.session)
        self.forecast_feature_snapshots = ForecastFeatureSnapshotRepository(
            self.session
        )
        self.user_contexts = UserContextRepository(self.session)
        self.decision_sessions = DecisionSessionRepository(self.session)
        self.recommendations = RecommendationRepository(self.session)
        self.recommendation_versions = RecommendationVersionRepository(self.session)
        self.outcomes = OutcomeRepository(self.session)

    def __enter__(self) -> UnitOfWork:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()
        if self._owns_session:
            self.session.close()

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()
