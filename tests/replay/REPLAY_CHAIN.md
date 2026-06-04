# Replay chain (TDS-006 §5) — E-01-S11

Historical replay for a pinned `as_of_date` loads data in order:

1. **CommodityRegistry** — `effective_from <= as_of_date` (version pinned)
2. **Observations** — `observed_at <= end_of_as_of_date(as_of_date)` (no future leakage)
3. **SignalSnapshot** — `(commodity_id, as_of_date, registry_id)` with `snapshot_hash`
4. **ForecastVersion** — published row linked to `snapshot_id` and `model_version`
5. **Decision stack** — `UserContext` → `DecisionSession` → `RecommendationVersion` with matching `formula_version`

## Replay hash inputs (E-01-S11 AC-3)

Minimum documented inputs for recommendation replay verification:

| Key | Source |
|-----|--------|
| `registry_id` | Active `CommodityRegistry` at `as_of_date` |
| `snapshot_hash` | `signal_snapshot.snapshot_hash` |
| `formula_version` | `recommendation_version.formula_version` |

Implemented in `backend/app/persistence/replay.py` (`build_replay_hash_inputs`, `REPLAY_HASH_INPUT_KEYS`).

Full TDS-006 §5 also references `model_version` on `ForecastVersion` for forecast replay; E-01 gate tests the three keys above per `E01_EXECUTION_PLAN.md` §7.3.
