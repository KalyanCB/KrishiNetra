"""Re-export synthetic panel for tests (PI10 Track E)."""

from backend.app.services.research.signal_effectiveness.synthetic_panel import (
    FIXTURE_DATA_SOURCE,
    build_synthetic_observation_panel,
)

__all__ = ["FIXTURE_DATA_SOURCE", "build_synthetic_observation_panel"]
