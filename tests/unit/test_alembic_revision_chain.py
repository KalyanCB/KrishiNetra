"""E-01-S01: Alembic revision chain integrity (no DB required)."""

from __future__ import annotations

from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_revision_chain_linear() -> None:
    root = Path(__file__).resolve().parents[2]
    cfg = Config(str(root / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    heads = script.get_heads()
    assert heads == ["0007_forecast_and_features"]
    revisions = list(script.walk_revisions(base="base", head=heads[0]))
    ids = [rev.revision for rev in reversed(revisions)]
    assert ids == [
        "0001_alembic_bootstrap",
        "0002_reference_entities",
        "0003_commodity_registry",
        "0004_data_quality_snapshot",
        "0005_observations_partitioned",
        "0006_signals_partitioned",
        "0007_forecast_and_features",
    ]


def test_bootstrap_has_no_business_tables_in_revision_doc() -> None:
    root = Path(__file__).resolve().parents[2]
    bootstrap = (
        root / "backend/app/persistence/migrations/versions/0001_alembic_bootstrap.py"
    )
    text = bootstrap.read_text(encoding="utf-8")
    assert "no business tables" in text.lower() or "no-op bootstrap" in text.lower()
