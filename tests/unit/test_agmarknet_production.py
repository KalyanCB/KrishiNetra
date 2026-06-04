"""E-03-S01: Agmarknet production OGD client, dedupe, and pipeline tests."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import httpx
import pytest

from backend.app.services.ingest.agmarknet.client import (
    OgdAgmarknetClient,
    OgdApiError,
    OgdClientConfig,
)
from backend.app.services.ingest.agmarknet.constants import OGD_RESOURCE_UUID
from backend.app.services.ingest.agmarknet.dedupe import (
    arrival_business_key,
    filter_new_arrival_drafts,
    filter_new_price_drafts,
    price_business_key,
)
from backend.app.services.ingest.agmarknet.mapper import (
    ArrivalObservationDraft,
    PriceObservationDraft,
)
from backend.app.services.ingest.agmarknet.pipeline import AgmarknetIngestPipeline

FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "agmarknet"
    / "ogd_telangana_sample.json"
)


def _price_draft(
    *,
    market_id: str = "mkt_tg_khammam_apmc",
    as_of: date = date(2022, 3, 26),
    price_type: str = "modal",
    quality_grade: str | None = "Cotton|FAQ",
    value: Decimal = Decimal("10500"),
) -> PriceObservationDraft:
    observed = datetime(2022, 3, 26, 18, 30, tzinfo=UTC)
    return PriceObservationDraft(
        market_id=market_id,
        commodity_id="cotton",
        price_type=price_type,
        value=value,
        unit="quintal",
        currency="INR",
        as_of_date=as_of,
        observed_at=observed,
        source="agmarknet",
        quality_grade=quality_grade,
        validation_status="received",
    )


def _arrival_draft(
    *,
    market_id: str = "mkt_tg_khammam_apmc",
    as_of: date = date(2022, 3, 26),
) -> ArrivalObservationDraft:
    observed = datetime(2022, 3, 26, 18, 30, tzinfo=UTC)
    return ArrivalObservationDraft(
        market_id=market_id,
        commodity_id="cotton",
        volume=Decimal("425"),
        unit="quintal",
        as_of_date=as_of,
        observed_at=observed,
        source="agmarknet",
        validation_status="received",
    )


def test_ogd_client_requires_api_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        OgdAgmarknetClient(OgdClientConfig(api_key=""))


def test_ogd_client_fetch_page_builds_resource_url() -> None:
    payload = {
        "total": 1,
        "records": [
            {
                "state": "Telangana",
                "district": "Khammam",
                "market": "Khammam",
                "commodity": "Cotton",
                "arrival_date": "26/03/2022",
                "modal_price": 10500,
            }
        ],
    }
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = payload
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    client = OgdAgmarknetClient(
        OgdClientConfig(api_key="test-key"),
        client=mock_client,
    )
    page = client.fetch_page(offset=0, limit=100, filters={"state": "Telangana"})

    assert page.record_count == 1
    assert page.total == 1
    mock_client.get.assert_called_once()
    call_args = mock_client.get.call_args
    url = call_args[0][0]
    params = call_args[1]["params"]
    assert OGD_RESOURCE_UUID in url
    assert params["api-key"] == "test-key"
    assert params["offset"] == 0
    assert params["limit"] == 100
    assert params["filters[state]"] == "Telangana"


def test_ogd_client_raises_on_error_envelope() -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {"error": "Key not authorised"}
    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.return_value = mock_response

    client = OgdAgmarknetClient(
        OgdClientConfig(api_key="bad-key"),
        client=mock_client,
    )
    with pytest.raises(OgdApiError, match="authorised"):
        client.fetch_page()


def test_ogd_client_retries_then_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    fail = MagicMock(spec=httpx.Response)
    fail.status_code = 503
    ok = MagicMock(spec=httpx.Response)
    ok.status_code = 200
    ok.json.return_value = {"total": 0, "records": []}

    mock_client = MagicMock(spec=httpx.Client)
    mock_client.get.side_effect = [fail, ok]
    sleeps: list[float] = []
    monkeypatch.setattr(
        "backend.app.services.ingest.agmarknet.client.time.sleep",
        lambda seconds: sleeps.append(seconds),
    )

    client = OgdAgmarknetClient(
        OgdClientConfig(api_key="k", max_retries=2, backoff_base_seconds=0.5),
        client=mock_client,
    )
    page = client.fetch_page()
    assert page.record_count == 0
    assert mock_client.get.call_count == 2
    assert sleeps == [0.5]


def test_ogd_client_iter_pages_pagination() -> None:
    page_one = {"total": 3, "records": [{"x": 1}, {"x": 2}]}
    page_two = {"total": 3, "records": [{"x": 3}]}

    mock_client = MagicMock(spec=httpx.Client)

    def _get(url: str, *, params: dict) -> httpx.Response:
        response = MagicMock(spec=httpx.Response)
        response.status_code = 200
        if params["offset"] == 0:
            response.json.return_value = page_one
        else:
            response.json.return_value = page_two
        return response

    mock_client.get.side_effect = _get

    client = OgdAgmarknetClient(
        OgdClientConfig(api_key="k", page_limit=2),
        client=mock_client,
    )
    rows = client.fetch_all()
    assert len(rows) == 3
    assert mock_client.get.call_count == 2


def test_price_business_key_includes_quality_grade() -> None:
    draft = _price_draft()
    assert price_business_key(draft) == (
        "mkt_tg_khammam_apmc",
        date(2022, 3, 26),
        "agmarknet",
        "modal",
        "Cotton|FAQ",
    )


def test_filter_new_price_drafts_skips_existing() -> None:
    draft = _price_draft()
    session = MagicMock()
    session.execute.return_value.all.return_value = [price_business_key(draft)]

    result = filter_new_price_drafts(session, [draft, _price_draft(price_type="min")])
    assert len(result.to_insert) == 1
    assert result.skipped == 1
    assert result.to_insert[0].price_type == "min"


def test_filter_new_arrival_drafts_skips_existing() -> None:
    draft = _arrival_draft()
    session = MagicMock()
    session.execute.return_value.all.return_value = [arrival_business_key(draft)]

    result = filter_new_arrival_drafts(session, [draft])
    assert result.to_insert == []
    assert result.skipped == 1


def test_pipeline_ingest_fixture_maps_cotton_rows() -> None:
    session = MagicMock()
    session.execute.return_value.all.return_value = []

    pipeline = AgmarknetIngestPipeline(session, write_quality_snapshot=False)
    result = pipeline.ingest_from_fixture(FIXTURE_PATH)

    assert result.ogd_rows_parsed == 4
    assert result.price_drafts > 0
    assert result.arrival_drafts == 1
    assert result.prices_inserted == result.price_drafts
    assert result.arrivals_inserted == 1
    assert session.execute.called


def test_pipeline_ingest_fixture_idempotent_second_run() -> None:
    session = MagicMock()
    existing_key = (
        "mkt_tg_khammam_apmc",
        date(2022, 3, 26),
        "agmarknet",
        "modal",
        "Cotton|FAQ",
    )
    session.execute.return_value.all.return_value = [existing_key]

    pipeline = AgmarknetIngestPipeline(session, write_quality_snapshot=False)
    result = pipeline.ingest_from_fixture(FIXTURE_PATH)

    assert result.prices_skipped_duplicate >= 1


def test_pipeline_ingest_from_ogd_mock_client() -> None:
    fixture_payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    mock_client = MagicMock()
    mock_client.fetch_all.return_value = fixture_payload["records"]

    session = MagicMock()
    session.execute.return_value.all.return_value = []

    pipeline = AgmarknetIngestPipeline(
        session, ogd_client=mock_client, write_quality_snapshot=False
    )
    result = pipeline.ingest_from_ogd(filters={"state": "Telangana"}, commit=False)

    assert result.ogd_rows_fetched == 4
    mock_client.fetch_all.assert_called_once_with(filters={"state": "Telangana"})
    session.commit.assert_not_called()


@pytest.mark.integration
def test_pipeline_fixture_integration(migrated_database: str) -> None:
    """Optional: full fixture ingest when DATABASE_URL + migrations available."""
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import Session
    from tests.integration.test_cotton_registry import _cleanup_cotton

    from backend.app.persistence.models.observation import (
        PriceObservationModel,
    )
    from backend.app.persistence.seeds.runner import SeedRunner
    from backend.app.spike.agmarknet.population import (
        delete_cotton_agmarknet_observations,
    )

    engine = create_engine(migrated_database, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            _cleanup_cotton(session)
            delete_cotton_agmarknet_observations(session)
            SeedRunner(session).apply("cotton")
            session.commit()

        with Session(engine) as session:
            pipeline = AgmarknetIngestPipeline(session)
            first = pipeline.ingest_from_fixture(FIXTURE_PATH)
            session.commit()
            second = pipeline.ingest_from_fixture(FIXTURE_PATH)
            session.commit()

            price_count = session.scalar(
                select(func.count())
                .select_from(PriceObservationModel)
                .where(
                    PriceObservationModel.source == "agmarknet",
                    PriceObservationModel.commodity_id == "cotton",
                )
            )

        assert first.total_inserted > 0
        assert second.total_inserted == 0
        assert second.prices_skipped_duplicate > 0
        assert price_count == first.prices_inserted
    finally:
        with Session(engine) as session:
            delete_cotton_agmarknet_observations(session)
            _cleanup_cotton(session)
            session.commit()
        engine.dispose()
