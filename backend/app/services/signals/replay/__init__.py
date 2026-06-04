"""PI9 Track D — deterministic signal replay validation."""

from backend.app.services.signals.replay.harness import (
    DEFAULT_REPLAY_CYCLES,
    CombinedSnapshotFingerprint,
    GeneratorReplayFingerprint,
    ReplayValidationResult,
    fingerprint_combined_snapshot,
    fingerprint_combined_snapshot_from_signals,
    fingerprint_market_bundle,
    fingerprint_market_cycle,
    fingerprint_weather_cycle,
    run_market_replay,
    run_weather_replay,
    summarize_results,
    validate_replay_cycles,
)

__all__ = [
    "DEFAULT_REPLAY_CYCLES",
    "CombinedSnapshotFingerprint",
    "GeneratorReplayFingerprint",
    "ReplayValidationResult",
    "fingerprint_combined_snapshot",
    "fingerprint_combined_snapshot_from_signals",
    "fingerprint_market_bundle",
    "fingerprint_market_cycle",
    "fingerprint_weather_cycle",
    "run_market_replay",
    "run_weather_replay",
    "summarize_results",
    "validate_replay_cycles",
]
