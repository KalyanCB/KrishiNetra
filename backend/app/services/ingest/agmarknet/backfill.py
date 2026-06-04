"""Historical Agmarknet backfill — date-window OGD pulls for Telangana cotton mandis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.persistence.models.observation import (
    ArrivalObservationModel,
    PriceObservationModel,
)
from backend.app.persistence.seeds.runner import SeedRunner
from backend.app.services.ingest.agmarknet.client import OgdAgmarknetClient
from backend.app.services.ingest.agmarknet.constants import (
    COTTON_COMMODITY_ID,
    SOURCE_AGMARKNET,
)
from backend.app.services.ingest.agmarknet.expected_markets import (
    load_expected_market_ids,
)
from backend.app.services.ingest.agmarknet.market_lookup import (
    load_market_lookup_from_seed,
)
from backend.app.services.ingest.agmarknet.pipeline import (
    AgmarknetIngestPipeline,
    build_ogd_client,
)

DEFAULT_BACKFILL_MONTHS = 36
MIN_BACKFILL_MONTHS = 24
TELANGANA_OGD_STATE = "Telangana"

@dataclass(frozen=True, slots=True)
class BackfillWindow:
    """Inclusive calendar window for historical pulls."""

    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start > self.end:
            msg = f"backfill start {self.start} after end {self.end}"
            raise ValueError(msg)

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


@dataclass(frozen=True, slots=True)
class AgmarknetBackfillChunkResult:
    """Counters for one arrival_date OGD pull."""

    arrival_date: date
    ogd_rows_fetched: int
    total_inserted: int
    prices_inserted: int
    arrivals_inserted: int
    prices_skipped_duplicate: int
    arrivals_skipped_duplicate: int


@dataclass(frozen=True, slots=True)
class AgmarknetBackfillResult:
    """Aggregated counters across a full backfill run."""

    window: BackfillWindow
    dry_run: bool
    days_requested: int
    days_fetched: int
    ogd_rows_fetched: int
    total_inserted: int
    prices_inserted: int
    arrivals_inserted: int
    prices_skipped_duplicate: int
    arrivals_skipped_duplicate: int
    chunk_results: tuple[AgmarknetBackfillChunkResult, ...] = ()

    @property
    def rows_loaded(self) -> int:
        return self.total_inserted


@dataclass(frozen=True, slots=True)
class MarketDateCoverage:
    """Per-market observation coverage inside the backfill window."""

    market_id: str
    distinct_dates: int
    min_as_of: date | None
    max_as_of: date | None


@dataclass(frozen=True, slots=True)
class MissingPeriod:
    """Contiguous calendar gap with no cotton Agmarknet rows for a market."""

    market_id: str
    start: date
    end: date
    days: int


@dataclass(frozen=True, slots=True)
class AgmarknetBackfillStats:
    """Post-load statistics for reporting and reproducibility checks."""

    window: BackfillWindow
    expected_market_ids: tuple[str, ...]
    price_row_count: int
    arrival_row_count: int
    total_row_count: int
    markets_with_data: int
    market_coverage: tuple[MarketDateCoverage, ...]
    distinct_as_of_dates: int
    min_as_of: date | None
    max_as_of: date | None
    missing_periods: tuple[MissingPeriod, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "window": {
                "start": self.window.start.isoformat(),
                "end": self.window.end.isoformat(),
                "days": self.window.days,
            },
            "expected_market_ids": list(self.expected_market_ids),
            "price_row_count": self.price_row_count,
            "arrival_row_count": self.arrival_row_count,
            "total_row_count": self.total_row_count,
            "markets_with_data": self.markets_with_data,
            "distinct_as_of_dates": self.distinct_as_of_dates,
            "min_as_of": self.min_as_of.isoformat() if self.min_as_of else None,
            "max_as_of": self.max_as_of.isoformat() if self.max_as_of else None,
            "market_coverage": [
                {
                    "market_id": m.market_id,
                    "distinct_dates": m.distinct_dates,
                    "min_as_of": m.min_as_of.isoformat() if m.min_as_of else None,
                    "max_as_of": m.max_as_of.isoformat() if m.max_as_of else None,
                }
                for m in self.market_coverage
            ],
            "missing_periods": [
                {
                    "market_id": p.market_id,
                    "start": p.start.isoformat(),
                    "end": p.end.isoformat(),
                    "days": p.days,
                }
                for p in self.missing_periods
            ],
        }


def default_backfill_end(*, today: date | None = None) -> date:
    """Inclusive end date for historical backfill (yesterday vs API lag)."""
    anchor = today or date.today()
    return anchor - timedelta(days=1)


def backfill_window_start(end: date, *, months: int) -> date:
    """Inclusive start date for N calendar months ending at ``end``."""
    month = end.month - months
    year = end.year
    while month < 1:
        month += 12
        year -= 1
    return date(year, month, 1)


def default_backfill_window(*, months: int = DEFAULT_BACKFILL_MONTHS) -> BackfillWindow:
    end = default_backfill_end()
    start = backfill_window_start(end, months=months)
    return BackfillWindow(start=start, end=end)


def format_ogd_arrival_date(day: date) -> str:
    """OGD ``filters[arrival_date]`` format (DD/MM/YYYY)."""
    return f"{day.day:02d}/{day.month:02d}/{day.year:04d}"


def iter_backfill_dates(window: BackfillWindow) -> list[date]:
    """Deterministic inclusive date list for reproducible iteration."""
    days: list[date] = []
    current = window.start
    while current <= window.end:
        days.append(current)
        current += timedelta(days=1)
    return days


def base_ogd_filters(*, arrival_date: date) -> dict[str, str]:
    """Telangana daily window filter for OGD pulls."""
    return {
        "state": TELANGANA_OGD_STATE,
        "arrival_date": format_ogd_arrival_date(arrival_date),
    }


class FixtureReplayOgdClient:
    """Replay a local OGD fixture for each date filter (CI without API key)."""

    def __init__(self, fixture_path: Path) -> None:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        records = payload.get("records")
        if not isinstance(records, list):
            msg = "fixture must contain records[]"
            raise ValueError(msg)
        self._records = [r for r in records if isinstance(r, dict)]

    def fetch_all(
        self,
        *,
        filters: dict[str, str] | None = None,
        limit: int | None = None,  # noqa: ARG002
    ) -> list[dict[str, Any]]:
        arrival_raw = (filters or {}).get("arrival_date")
        rows: list[dict[str, Any]] = []
        for record in self._records:
            row = dict(record)
            if arrival_raw:
                row["arrival_date"] = arrival_raw
            rows.append(row)
        return rows


class AgmarknetBackfillPipeline:
    """Orchestrate per-day OGD pulls through the production ingest pipeline."""

    def __init__(
        self,
        session: Session,
        *,
        ogd_client: OgdAgmarknetClient | FixtureReplayOgdClient,
        seed_cotton: bool = True,
        write_quality_snapshot: bool = True,
    ) -> None:
        self._session = session
        self._ogd_client = ogd_client
        self._seed_cotton = seed_cotton
        self._write_quality_snapshot = write_quality_snapshot
        lookup = load_market_lookup_from_seed()
        self._pipeline = AgmarknetIngestPipeline(
            session,
            market_lookup=lookup,
            ogd_client=ogd_client
            if isinstance(ogd_client, OgdAgmarknetClient)
            else None,
            write_quality_snapshot=False,
        )
        self._fixture_client = (
            ogd_client if isinstance(ogd_client, FixtureReplayOgdClient) else None
        )

    def run(
        self,
        window: BackfillWindow,
        *,
        dry_run: bool = False,
        commit_per_day: bool = True,
    ) -> AgmarknetBackfillResult:
        if self._seed_cotton:
            SeedRunner(self._session).apply("cotton")
            self._session.flush()

        chunk_results: list[AgmarknetBackfillChunkResult] = []
        ogd_rows_fetched = 0
        total_inserted = 0
        prices_inserted = 0
        arrivals_inserted = 0
        prices_skipped = 0
        arrivals_skipped = 0

        for day in iter_backfill_dates(window):
            chunk = self._ingest_day(day, commit=commit_per_day and not dry_run)
            chunk_results.append(chunk)
            ogd_rows_fetched += chunk.ogd_rows_fetched
            total_inserted += chunk.total_inserted
            prices_inserted += chunk.prices_inserted
            arrivals_inserted += chunk.arrivals_inserted
            prices_skipped += chunk.prices_skipped_duplicate
            arrivals_skipped += chunk.arrivals_skipped_duplicate
            if not dry_run and commit_per_day:
                self._session.commit()
            elif dry_run:
                self._session.rollback()

        if self._write_quality_snapshot and not dry_run:
            from backend.app.services.quality.snapshot_service import (
                DataQualitySnapshotService,
            )

            DataQualitySnapshotService(self._session).record_after_agmarknet_backfill(
                window_start=window.start,
                window_end=window.end,
            )

        return AgmarknetBackfillResult(
            window=window,
            dry_run=dry_run,
            days_requested=window.days,
            days_fetched=len(chunk_results),
            ogd_rows_fetched=ogd_rows_fetched,
            total_inserted=total_inserted,
            prices_inserted=prices_inserted,
            arrivals_inserted=arrivals_inserted,
            prices_skipped_duplicate=prices_skipped,
            arrivals_skipped_duplicate=arrivals_skipped,
            chunk_results=tuple(chunk_results),
        )

    def _ingest_day(self, day: date, *, commit: bool) -> AgmarknetBackfillChunkResult:
        filters = base_ogd_filters(arrival_date=day)
        if self._fixture_client is not None:
            raw_rows = self._fixture_client.fetch_all(filters=filters)
            payload = {"records": raw_rows}
            result = self._pipeline.ingest_ogd_payload(payload)
        else:
            result = self._pipeline.ingest_from_ogd(filters=filters, commit=commit)

        return AgmarknetBackfillChunkResult(
            arrival_date=day,
            ogd_rows_fetched=result.ogd_rows_fetched,
            total_inserted=result.total_inserted,
            prices_inserted=result.prices_inserted,
            arrivals_inserted=result.arrivals_inserted,
            prices_skipped_duplicate=result.prices_skipped_duplicate,
            arrivals_skipped_duplicate=result.arrivals_skipped_duplicate,
        )


def build_backfill_ogd_client(api_key: str) -> OgdAgmarknetClient:
    """Production OGD client for historical pulls."""
    return build_ogd_client(api_key)


def compute_backfill_stats(
    session: Session,
    window: BackfillWindow,
    *,
    expected_market_ids: tuple[str, ...] | None = None,
) -> AgmarknetBackfillStats:
    """Summarize cotton Agmarknet rows in DB for the backfill window."""
    markets = expected_market_ids or load_expected_market_ids()

    price_count = _count_observations(
        session,
        model=PriceObservationModel,
        window=window,
        market_ids=markets,
    )
    arrival_count = _count_observations(
        session,
        model=ArrivalObservationModel,
        window=window,
        market_ids=markets,
    )

    market_coverage = _market_date_coverage(session, window=window, market_ids=markets)
    dates_present = _distinct_as_of_dates(session, window=window, market_ids=markets)
    min_as_of, max_as_of = _global_as_of_bounds(
        session, window=window, market_ids=markets
    )
    missing = find_missing_periods(
        window,
        market_ids=markets,
        dates_by_market=_dates_by_market(session, window=window, market_ids=markets),
    )

    return AgmarknetBackfillStats(
        window=window,
        expected_market_ids=markets,
        price_row_count=price_count,
        arrival_row_count=arrival_count,
        total_row_count=price_count + arrival_count,
        markets_with_data=sum(1 for m in market_coverage if m.distinct_dates > 0),
        market_coverage=market_coverage,
        distinct_as_of_dates=len(dates_present),
        min_as_of=min_as_of,
        max_as_of=max_as_of,
        missing_periods=missing,
    )


def find_missing_periods(
    window: BackfillWindow,
    *,
    market_ids: tuple[str, ...],
    dates_by_market: dict[str, set[date]],
) -> tuple[MissingPeriod, ...]:
    """Contiguous gaps where a seed market has no Agmarknet cotton rows."""
    periods: list[MissingPeriod] = []
    for market_id in market_ids:
        present = dates_by_market.get(market_id, set())
        gap_start: date | None = None
        current = window.start
        while current <= window.end:
            if current in present:
                if gap_start is not None:
                    gap_end = current - timedelta(days=1)
                    periods.append(
                        MissingPeriod(
                            market_id=market_id,
                            start=gap_start,
                            end=gap_end,
                            days=(gap_end - gap_start).days + 1,
                        )
                    )
                    gap_start = None
            elif gap_start is None:
                gap_start = current
            current += timedelta(days=1)
        if gap_start is not None:
            periods.append(
                MissingPeriod(
                    market_id=market_id,
                    start=gap_start,
                    end=window.end,
                    days=(window.end - gap_start).days + 1,
                )
            )
    return tuple(periods)


def render_backfill_report_markdown(
    *,
    result: AgmarknetBackfillResult | None,
    stats: AgmarknetBackfillStats,
    fixture_mode: bool = False,
) -> str:
    """Render PI6 Track B report body (written by CLI to docs/reviews/)."""
    lines = [
        "# Historical Agmarknet Backfill Report — PI6 Track B",
        "",
        "**Date:** 2026-06-04",
        "**PI:** PI6 Track B (KDO — Telangana cotton mandi historical backfill)",
        "**Status:** Backfill framework complete — production pipeline + date-window OGD",
        "**Seed:** E-02 `cotton.json` (4 Telangana mandis with `source_identifiers.agmarknet`)",
        "",
        "---",
        "",
        "## 1. Verdict",
        "",
        "| Question | Answer |",
        "|----------|--------|",
        f"| Target window (days) | **{stats.window.days}** ({stats.window.start} → {stats.window.end}) |",
        f"| Minimum 24 mo / preferred 36 mo | **{'PASS' if stats.window.days >= 730 else 'PARTIAL'}** / "
        f"**{'PASS' if stats.window.days >= 1095 else 'PARTIAL'}** |",
        f"| Seed markets expected | **{len(stats.expected_market_ids)}** |",
        f"| Markets with data | **{stats.markets_with_data}** |",
        f"| Total observation rows | **{stats.total_row_count}** (price {stats.price_row_count}, "
        f"arrival {stats.arrival_row_count}) |",
        f"| Distinct `as_of_date` values | **{stats.distinct_as_of_dates}** |",
        f"| Fixture replay mode | **{'Yes' if fixture_mode else 'No'}** |",
        "",
        "---",
        "",
        "## 2. Window and Coverage",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Start (inclusive) | `{stats.window.start.isoformat()}` |",
        f"| End (inclusive) | `{stats.window.end.isoformat()}` |",
        f"| `as_of_date` min | `{stats.min_as_of}` |",
        f"| `as_of_date` max | `{stats.max_as_of}` |",
        "",
        "### Per-market",
        "",
        "| `market_id` | Distinct dates | Min | Max |",
        "|-------------|----------------|-----|-----|",
    ]
    for row in stats.market_coverage:
        lines.append(
            f"| `{row.market_id}` | {row.distinct_dates} | "
            f"{row.min_as_of or '—'} | {row.max_as_of or '—'} |"
        )
    lines.extend(
        [
            "",
            "---",
            "",
            "## 3. Missing periods (sample)",
            "",
        ]
    )
    if not stats.missing_periods:
        lines.append("_No gaps detected for markets with full daily coverage._")
    else:
        lines.append("| Market | Start | End | Days |")
        lines.append("|--------|-------|-----|------|")
        for period in stats.missing_periods[:20]:
            lines.append(
                f"| `{period.market_id}` | {period.start} | {period.end} | {period.days} |"
            )
        if len(stats.missing_periods) > 20:
            lines.append(f"\n_…and {len(stats.missing_periods) - 20} more gaps._")

    if result is not None:
        lines.extend(
            [
                "",
                "---",
                "",
                "## 4. Last ingest run",
                "",
                "| Metric | Value |",
                "|--------|-------|",
                f"| Dry run | {result.dry_run} |",
                f"| Days fetched | {result.days_fetched} |",
                f"| OGD rows fetched | {result.ogd_rows_fetched} |",
                f"| Rows inserted (run) | {result.total_inserted} |",
                f"| Price / arrival inserted | {result.prices_inserted} / {result.arrivals_inserted} |",
                f"| Duplicates skipped (price / arrival) | "
                f"{result.prices_skipped_duplicate} / {result.arrivals_skipped_duplicate} |",
            ]
        )

    lines.extend(
        [
            "",
            "---",
            "",
            "## 5. Deliverables",
            "",
            "| Artifact | Path |",
            "|----------|------|",
            "| Backfill service | `backend/app/services/ingest/agmarknet/backfill.py` |",
            "| Partition migration | `backend/app/persistence/migrations/versions/0010_observation_partitions_backfill.py` |",
            "| CLI | `scripts/agmarknet_backfill.py` |",
            "| Unit tests | `tests/unit/test_agmarknet_backfill.py` |",
            "",
            "---",
            "",
            "## 6. Reproducibility",
            "",
            "- Deterministic date iteration (`iter_backfill_dates`).",
            "- Business-key dedupe via production `AgmarknetIngestPipeline`.",
            "- CI: `--fixture` replays `tests/fixtures/agmarknet/ogd_telangana_sample.json`.",
            "- Live: `OGD_API_KEY` + `--start-date` / `--end-date` (DD/MM/YYYY filters per day).",
            "",
        ]
    )
    return "\n".join(lines)


def _count_observations(
    session: Session,
    *,
    model: type[PriceObservationModel] | type[ArrivalObservationModel],
    window: BackfillWindow,
    market_ids: tuple[str, ...],
) -> int:
    stmt = (
        select(func.count())
        .select_from(model)
        .where(
            model.source == SOURCE_AGMARKNET,
            model.commodity_id == COTTON_COMMODITY_ID,
            model.market_id.in_(market_ids),
            model.as_of_date >= window.start,
            model.as_of_date <= window.end,
        )
    )
    return int(session.scalar(stmt) or 0)


def _market_date_coverage(
    session: Session,
    *,
    window: BackfillWindow,
    market_ids: tuple[str, ...],
) -> tuple[MarketDateCoverage, ...]:
    rows: list[MarketDateCoverage] = []
    for market_id in market_ids:
        stmt = select(
            func.count(func.distinct(PriceObservationModel.as_of_date)),
            func.min(PriceObservationModel.as_of_date),
            func.max(PriceObservationModel.as_of_date),
        ).where(
            PriceObservationModel.source == SOURCE_AGMARKNET,
            PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
            PriceObservationModel.market_id == market_id,
            PriceObservationModel.as_of_date >= window.start,
            PriceObservationModel.as_of_date <= window.end,
        )
        distinct, min_d, max_d = session.execute(stmt).one()
        rows.append(
            MarketDateCoverage(
                market_id=market_id,
                distinct_dates=int(distinct or 0),
                min_as_of=min_d,
                max_as_of=max_d,
            )
        )
    return tuple(rows)


def _distinct_as_of_dates(
    session: Session,
    *,
    window: BackfillWindow,
    market_ids: tuple[str, ...],
) -> set[date]:
    stmt = select(PriceObservationModel.as_of_date).where(
        PriceObservationModel.source == SOURCE_AGMARKNET,
        PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
        PriceObservationModel.market_id.in_(market_ids),
        PriceObservationModel.as_of_date >= window.start,
        PriceObservationModel.as_of_date <= window.end,
    )
    return {row[0] for row in session.execute(stmt).all()}


def _global_as_of_bounds(
    session: Session,
    *,
    window: BackfillWindow,
    market_ids: tuple[str, ...],
) -> tuple[date | None, date | None]:
    stmt = select(
        func.min(PriceObservationModel.as_of_date),
        func.max(PriceObservationModel.as_of_date),
    ).where(
        PriceObservationModel.source == SOURCE_AGMARKNET,
        PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
        PriceObservationModel.market_id.in_(market_ids),
        PriceObservationModel.as_of_date >= window.start,
        PriceObservationModel.as_of_date <= window.end,
    )
    min_d, max_d = session.execute(stmt).one()
    return min_d, max_d


def _dates_by_market(
    session: Session,
    *,
    window: BackfillWindow,
    market_ids: tuple[str, ...],
) -> dict[str, set[date]]:
    stmt = select(
        PriceObservationModel.market_id,
        PriceObservationModel.as_of_date,
    ).where(
        PriceObservationModel.source == SOURCE_AGMARKNET,
        PriceObservationModel.commodity_id == COTTON_COMMODITY_ID,
        PriceObservationModel.market_id.in_(market_ids),
        PriceObservationModel.as_of_date >= window.start,
        PriceObservationModel.as_of_date <= window.end,
    )
    by_market: dict[str, set[date]] = {m: set() for m in market_ids}
    for market_id, as_of in session.execute(stmt).all():
        by_market.setdefault(str(market_id), set()).add(as_of)
    return by_market
