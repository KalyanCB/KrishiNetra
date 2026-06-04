"""Forward monthly partitions for Agmarknet historical backfill (PI6 Track B / G7).

Revision ID: 0010_partition_backfill
Revises: 0009_weather_observations
Create Date: 2026-06-04

Adds price_observation / arrival_observation children for 2023-06 through 2026-12
(0005 already created 2026_06). DEFAULT partition remains for overflow.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from alembic import op

revision: str = "0010_partition_backfill"
down_revision: str | None = "0009_weather_observations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 36-mo backfill from 2026-06-04 → 2023-06-01; include through Dec 2026 for ops headroom.
_PARTITION_RANGE_START = date(2023, 6, 1)
_PARTITION_RANGE_END = date(2027, 1, 1)
_SKIP_SUFFIXES = frozenset({"2026_06"})


def _month_starts(start: date, end: date) -> list[tuple[date, date, str]]:
    """Yield (from, to, suffix) for each calendar month in [start, end)."""
    months: list[tuple[date, date, str]] = []
    year, month = start.year, start.month
    while date(year, month, 1) < end:
        month_start = date(year, month, 1)
        month_end = (
            date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
        )
        suffix = f"{year}_{month:02d}"
        months.append((month_start, month_end, suffix))
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
    return months


def _create_observation_partitions(table: str) -> list[str]:
    created: list[str] = []
    for month_start, month_end, suffix in _month_starts(
        _PARTITION_RANGE_START, _PARTITION_RANGE_END
    ):
        if suffix in _SKIP_SUFFIXES:
            continue
        child = f"{table}_{suffix}"
        created.append(child)
        op.execute(
            f"""
            CREATE TABLE {child} PARTITION OF {table}
                FOR VALUES FROM ('{month_start.isoformat()}')
                TO ('{month_end.isoformat()}')
            """
        )
    return created


def upgrade() -> None:
    _create_observation_partitions("price_observation")
    _create_observation_partitions("arrival_observation")


def downgrade() -> None:
    for _month_start, _month_end, suffix in _month_starts(
        _PARTITION_RANGE_START, _PARTITION_RANGE_END
    ):
        if suffix in _SKIP_SUFFIXES:
            continue
        op.execute(f"DROP TABLE IF EXISTS price_observation_{suffix}")
        op.execute(f"DROP TABLE IF EXISTS arrival_observation_{suffix}")
