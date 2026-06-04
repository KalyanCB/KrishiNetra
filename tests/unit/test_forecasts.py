"""E-01-S06: Forecast, ForecastVersion, and feature store persistence tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.persistence.models.forecast import (
    FeatureSetModel,
    FeatureVectorModel,
    ForecastModel,
    ForecastStatus,
    ForecastVersionModel,
)
from backend.app.persistence.models.quality import DataQualitySnapshotModel
from backend.app.persistence.models.reference import CommodityModel, CommodityStatus
from backend.app.persistence.models.registry import CommodityRegistryModel
from backend.app.persistence.models.signal import (
    SignalSnapshotModel,
    StructuredSignalModel,
)
from backend.app.persistence.repositories.forecast import (
    FeatureSetRepository,
    FeatureVectorRepository,
    ForecastRepository,
    ForecastVersionRepository,
)
from backend.app.persistence.repositories.quality import DataQualitySnapshotRepository
from backend.app.persistence.repositories.registry import CommodityRegistryRepository
from backend.app.persistence.repositories.signal import (
    SignalSnapshotRepository,
    StructuredSignalRepository,
)
from backend.app.persistence.validation.forecast import (
    ForecastValidationError,
    validate_forecast_confidence,
    validate_forecast_version_horizons,
)
from shared.domain.enums import AgentType, Direction
from shared.persistence.contracts import ImmutableVersionUpdateError


def _decision_rules() -> dict:
    return {
        "msp_proximity_pct": 0.03,
        "default_partial_sell_pct": 0.50,
        "formula_version": "v1.0.0",
    }


def _horizon_payload(*, confidence: Decimal = Decimal("0.80")) -> dict:
    return {
        "point": 5500.0,
        "band_low": 5200.0,
        "band_high": 5800.0,
        "direction": Direction.BULLISH.value,
        "forecast_confidence": float(confidence),
    }


def _seed_registry(session: Session, *, commodity_id: str) -> CommodityRegistryModel:
    commodity = CommodityModel(
        commodity_id=commodity_id,
        name=f"Forecast Test {commodity_id}",
        status=CommodityStatus.DRAFT.value,
    )
    session.add(commodity)
    session.flush()
    registry = CommodityRegistryModel(
        registry_id=uuid4(),
        commodity_id=commodity_id,
        version="1.0.0",
        effective_from=date(2026, 1, 1),
        is_active=True,
        required_agents=["Market", "Futures"],
        decision_rules=_decision_rules(),
    )
    CommodityRegistryRepository(session).insert_version(registry)
    return registry


def _seed_snapshot(
    session: Session,
    *,
    commodity_id: str,
    registry: CommodityRegistryModel,
) -> SignalSnapshotModel:
    quality = DataQualitySnapshotModel(
        quality_snapshot_id=uuid4(),
        commodity_id=commodity_id,
        as_of_date=date(2026, 6, 4),
        registry_id=registry.registry_id,
        source_health={"agmarknet": "fresh"},
        overall_quality_score=Decimal("0.90"),
        futures_feed_ok=True,
        confidence_penalty_factor=Decimal("0"),
    )
    DataQualitySnapshotRepository(session).insert_snapshot(quality)

    signal_repo = StructuredSignalRepository(session)
    observed = datetime(2026, 6, 4, 12, 0, tzinfo=UTC)
    signal_ids: list[str] = []
    for agent in AgentType:
        row = StructuredSignalModel(
            signal_id=uuid4(),
            agent_type=agent.value,
            commodity_id=commodity_id,
            as_of_date=date(2026, 6, 4),
            as_of_timestamp=observed,
            value=Decimal("0.50"),
            direction=Direction.NEUTRAL.value,
            magnitude=Decimal("0.30"),
            confidence=Decimal("0.70"),
            registry_id=registry.registry_id,
        )
        signal_repo.insert_signal(row)
        signal_ids.append(str(row.signal_id))

    snapshot = SignalSnapshotModel(
        snapshot_id=uuid4(),
        commodity_id=commodity_id,
        as_of_date=date(2026, 6, 4),
        registry_id=registry.registry_id,
        signal_ids=signal_ids,
        snapshot_hash="abc123" * 10 + "abcd",
        data_quality_snapshot_id=quality.quality_snapshot_id,
    )
    SignalSnapshotRepository(session).insert(snapshot)
    return snapshot


def test_forecast_confidence_bounds_rejects_above_one() -> None:
    with pytest.raises(ForecastValidationError, match="\\[0, 1\\]"):
        validate_forecast_confidence(Decimal("1.05"), field_name="forecast_confidence")


def test_forecast_version_horizons_validate_confidence() -> None:
    bad = _horizon_payload(confidence=Decimal("1.2"))
    with pytest.raises(ForecastValidationError, match="forecast_confidence"):
        validate_forecast_version_horizons(
            horizon_30=bad,
            horizon_60=_horizon_payload(),
            horizon_90=_horizon_payload(),
        )


def test_forecast_version_immutable() -> None:
    from unittest.mock import MagicMock

    session = MagicMock(spec=Session)
    repo = ForecastVersionRepository(session)
    with pytest.raises(ImmutableVersionUpdateError, match="UPDATE blocked"):
        repo.update(ForecastVersionModel())  # type: ignore[call-arg]


def _cleanup_forecast_fixtures(
    session: Session,
    *,
    commodity_id: str,
    as_of_date: date,
) -> None:
    session.execute(
        text(
            "DELETE FROM forecast_version WHERE commodity_id = :cid AND as_of_date = :dt"
        ),
        {"cid": commodity_id, "dt": as_of_date},
    )
    session.execute(
        text("DELETE FROM feature_vector WHERE feature_set_id IN "
             "(SELECT feature_set_id FROM feature_set WHERE commodity_id = :cid)"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM feature_set WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM forecast WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    session.execute(
        text("DELETE FROM signal_snapshot WHERE commodity_id = :cid AND as_of_date = :dt"),
        {"cid": commodity_id, "dt": as_of_date},
    )
    session.execute(
        text(
            "DELETE FROM structured_signal WHERE commodity_id = :cid AND as_of_date = :dt"
        ),
        {"cid": commodity_id, "dt": as_of_date},
    )
    session.execute(
        text(
            "DELETE FROM data_quality_snapshot WHERE commodity_id = :cid AND as_of_date = :dt"
        ),
        {"cid": commodity_id, "dt": as_of_date},
    )
    session.execute(
        text("DELETE FROM commodity_registry WHERE commodity_id = :cid"),
        {"cid": commodity_id},
    )
    commodity = session.get(CommodityModel, commodity_id)
    if commodity is not None:
        session.delete(commodity)
    session.commit()


@pytest.mark.integration
def test_forecast_version_linked_to_snapshot(migrated_database: str) -> None:
    commodity_id = f"fcst_link_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        registry = _seed_registry(session, commodity_id=commodity_id)
        snapshot = _seed_snapshot(
            session, commodity_id=commodity_id, registry=registry
        )

        forecast = ForecastRepository(session).insert(
            ForecastModel(forecast_id=uuid4(), commodity_id=commodity_id)
        )
        feature_set = FeatureSetRepository(session).insert_feature_set(
            FeatureSetModel(
                feature_set_id=uuid4(),
                commodity_id=commodity_id,
                as_of_date=date(2026, 6, 4),
                registry_id=registry.registry_id,
                feature_hash="deadbeef" * 8,
            )
        )
        FeatureVectorRepository(session).insert_vector(
            FeatureVectorModel(
                feature_set_id=feature_set.feature_set_id,
                feature_name="market_momentum_30d",
                feature_value={"category": "Market", "value": 0.12},
            )
        )

        version = ForecastVersionRepository(session).insert_version(
            ForecastVersionModel(
                forecast_version_id=uuid4(),
                forecast_id=forecast.forecast_id,
                commodity_id=commodity_id,
                as_of_date=date(2026, 6, 4),
                registry_id=registry.registry_id,
                snapshot_id=snapshot.snapshot_id,
                model_family="candidate_a",
                model_version="v0.1.0",
                horizon_30=_horizon_payload(),
                horizon_60=_horizon_payload(),
                horizon_90=_horizon_payload(),
                feature_set_ref=feature_set.feature_set_id,
                composed_signal_refs=snapshot.signal_ids,
                status=ForecastStatus.COMPLETE.value,
                is_published=True,
            )
        )
        session.commit()

        loaded = ForecastVersionRepository(session).get_published(
            commodity_id,
            date(2026, 6, 4),
            registry.registry_id,
        )
        assert loaded is not None
        assert loaded.forecast_version_id == version.forecast_version_id
        assert loaded.snapshot_id == snapshot.snapshot_id
        assert loaded.feature_set_ref == feature_set.feature_set_id
        assert loaded.horizon_30["forecast_confidence"] == 0.80

        _cleanup_forecast_fixtures(
            session, commodity_id=commodity_id, as_of_date=date(2026, 6, 4)
        )
    engine.dispose()


@pytest.mark.integration
def test_forecast_version_unique_per_day_model(migrated_database: str) -> None:
    commodity_id = f"fcst_uq_{uuid4().hex[:8]}"
    engine = create_engine(migrated_database, pool_pre_ping=True)
    with Session(engine) as session:
        registry = _seed_registry(session, commodity_id=commodity_id)
        snapshot = _seed_snapshot(
            session, commodity_id=commodity_id, registry=registry
        )
        forecast = ForecastRepository(session).insert(
            ForecastModel(forecast_id=uuid4(), commodity_id=commodity_id)
        )
        repo = ForecastVersionRepository(session)
        repo.insert_version(
            ForecastVersionModel(
                forecast_version_id=uuid4(),
                forecast_id=forecast.forecast_id,
                commodity_id=commodity_id,
                as_of_date=date(2026, 6, 4),
                registry_id=registry.registry_id,
                snapshot_id=snapshot.snapshot_id,
                model_version="v0.1.0",
                horizon_30=_horizon_payload(),
                horizon_60=_horizon_payload(),
                horizon_90=_horizon_payload(),
                is_published=True,
            )
        )
        session.commit()

        duplicate = ForecastVersionModel(
            forecast_version_id=uuid4(),
            forecast_id=forecast.forecast_id,
            commodity_id=commodity_id,
            as_of_date=date(2026, 6, 4),
            registry_id=registry.registry_id,
            snapshot_id=snapshot.snapshot_id,
            model_version="v0.1.0",
            horizon_30=_horizon_payload(),
            horizon_60=_horizon_payload(),
            horizon_90=_horizon_payload(),
        )
        session.add(duplicate)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        _cleanup_forecast_fixtures(
            session, commodity_id=commodity_id, as_of_date=date(2026, 6, 4)
        )
    engine.dispose()
