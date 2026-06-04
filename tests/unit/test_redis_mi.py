"""E-01-S09: Redis MI projection client and cache contract tests."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import fakeredis

from backend.app.cache.mi_projection import (
    DEFAULT_MI_TTL_SECONDS,
    RedisMIProjectionClient,
    build_mi_cache_key,
)
from backend.app.services.mi_snapshot_materializer import (
    MISnapshotMaterializer,
    build_mi_payload,
)
from shared.contracts.mi_snapshot import MISnapshotPayload


def test_redis_key_format() -> None:
    """Key matches ``mi:{commodity_id}:{as_of_date}`` (AC-1)."""
    assert build_mi_cache_key("cotton", date(2026, 6, 4)) == "mi:cotton:2026-06-04"
    assert build_mi_cache_key("cotton", "2026-06-04") == "mi:cotton:2026-06-04"


def test_redis_mi_roundtrip() -> None:
    """JSON set/get round-trip via fakeredis (AC-2)."""
    fake = fakeredis.FakeRedis(decode_responses=True)
    client = RedisMIProjectionClient(fake, default_ttl_seconds=3600)
    key = build_mi_cache_key("cotton", date(2026, 6, 4))
    payload = {
        "mi_snapshot_id": str(uuid4()),
        "commodity_id": "cotton",
        "as_of_date": "2026-06-04",
        "registry_id": str(uuid4()),
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "snapshot_id": str(uuid4()),
        "snapshot_hash": "abc123",
        "partial": True,
    }

    assert client.set_mi_snapshot(key, payload) is True
    loaded = client.get_mi_snapshot(key)
    assert loaded == payload


def test_default_ttl_from_settings_constant() -> None:
    assert DEFAULT_MI_TTL_SECONDS == 48 * 3600


def test_graceful_degrade_on_redis_failure() -> None:
    """Read returns miss and health probe does not raise (AC-5)."""
    client = RedisMIProjectionClient(redis_url="redis://127.0.0.1:1")
    key = build_mi_cache_key("cotton", date(2026, 6, 4))

    assert client.get_mi_snapshot(key) is None
    assert client.set_mi_snapshot(key, {"commodity_id": "cotton"}) is False
    assert client.ping() is False


def test_build_mi_payload_partial_shape() -> None:
    from backend.app.persistence.models.forecast import ForecastVersionModel
    from backend.app.persistence.models.signal import SignalSnapshotModel

    snapshot_id = uuid4()
    registry_id = uuid4()
    forecast_id = uuid4()
    snapshot = SignalSnapshotModel(
        snapshot_id=snapshot_id,
        commodity_id="cotton",
        as_of_date=date(2026, 6, 4),
        registry_id=registry_id,
        signal_ids=[str(uuid4())],
        snapshot_hash="deadbeef",
    )
    forecast = ForecastVersionModel(
        forecast_version_id=forecast_id,
        as_of_date=date(2026, 6, 4),
        forecast_id=uuid4(),
        commodity_id="cotton",
        registry_id=registry_id,
        snapshot_id=snapshot_id,
        model_version="test-v1",
        horizon_30={
            "point": 5500.0,
            "band_low": 5200.0,
            "band_high": 5800.0,
            "direction": "bullish",
            "forecast_confidence": 0.8,
        },
        is_published=True,
    )

    payload = build_mi_payload(snapshot=snapshot, forecast=forecast, quality=None)
    assert payload.partial is True
    assert payload.forecast_version_id == forecast_id
    assert payload.forecast_confidence_30 == 0.8
    assert payload.horizon_summaries is not None
    assert len(payload.horizon_summaries) == 1


def test_materializer_caches_payload() -> None:
    from backend.app.persistence.models.signal import SignalSnapshotModel

    snapshot = SignalSnapshotModel(
        snapshot_id=uuid4(),
        commodity_id="cotton",
        as_of_date=date(2026, 6, 4),
        registry_id=uuid4(),
        signal_ids=[str(uuid4())],
        snapshot_hash="cafebabe",
    )

    class FakeSignalRepo:
        def get_snapshot(
            self,
            *,
            commodity_id: str,
            as_of_date: date,
            registry_id,
        ):
            assert commodity_id == "cotton"
            return snapshot

    class FakeForecastRepo:
        def get_published(self, commodity_id: str, as_of_date: date, registry_id):
            return None

    class FakeQualityRepo:
        def get_snapshot(self, quality_snapshot_id):
            return None

    class FakeUow:
        signal_snapshots = FakeSignalRepo()
        forecast_versions = FakeForecastRepo()
        quality_snapshots = FakeQualityRepo()

    fake = fakeredis.FakeRedis(decode_responses=True)
    cache = RedisMIProjectionClient(fake)
    materializer = MISnapshotMaterializer(FakeUow(), cache)  # type: ignore[arg-type]

    result = materializer.materialize_and_cache(
        "cotton",
        date(2026, 6, 4),
        snapshot.registry_id,
    )
    assert isinstance(result, MISnapshotPayload)
    key = build_mi_cache_key("cotton", date(2026, 6, 4))
    cached = cache.get_mi_snapshot(key)
    assert cached is not None
    assert cached["commodity_id"] == "cotton"
    assert cached["snapshot_hash"] == "cafebabe"
