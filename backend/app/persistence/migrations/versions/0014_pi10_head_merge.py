"""Merge PI10 parallel heads (Futures, Forecast, Policy).

Revision ID: 0014_pi10_head_merge
Revises: 0013_futures_observations, 0013_forecast_feature_snapshot, 0013_policy_observations
Create Date: 2026-06-04

No-op merge revision — coordinates PI10 Tracks A/B/C migration branches.
"""

from collections.abc import Sequence

revision: str = "0014_pi10_head_merge"
down_revision: str | tuple[str, ...] | None = (
    "0013_futures_observations",
    "0013_forecast_feature_snapshot",
    "0013_policy_observations",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
