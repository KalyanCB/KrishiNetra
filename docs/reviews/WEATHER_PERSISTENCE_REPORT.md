# Weather Observation Persistence Report — PI6 Track C

**Date:** 2026-06-04  
**PI:** PI6 Track C (KDO — E-01 weather observation DDL)  
**Status:** Persistence layer complete — no ingest pipeline, no signal agent  
**Strategy baseline:** [WEATHER_DATA_STRATEGY_V1.md](../research/WEATHER_DATA_STRATEGY_V1.md)  
**Spike baseline:** [WEATHER_SPIKE_REPORT.md](./WEATHER_SPIKE_REPORT.md)  
**HEAD:** `894a6a8` @ `main`

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Weather observation table migrated? | **Yes** — `weather_observation` @ `0009_weather_observations` |
| Append-only repository? | **Yes** — `WeatherObservationRepository.insert_observation` |
| Region/district linkage? | **Yes** — `region_id` FK + optional `district_name`; IMD refs in `provenance` |
| Source tiering fields? | **Yes** — `source` ∈ `{nasa_power, imd}` |
| Signal generation / forecasting? | **No** — out of scope (SI-02 DDL only) |

**Overall:** **PASS** — closes E-01 gap **SI-02** for observation persistence; E-03 ingest still required.

---

## 2. Schema Summary

| Column | Type | Notes |
|--------|------|-------|
| `observation_id`, `as_of_date` | UUID, DATE | Composite PK; monthly RANGE partition |
| `region_id`, `commodity_id` | VARCHAR(64) | District linkage via E-02 `region`; commodity for belt queries |
| `district_name` | VARCHAR(255) | Optional label (e.g. Khammam) when ingest has district text |
| `rainfall_mm` | NUMERIC(10,4) | IMD Daily Actual / NASA `PRECTOTCORR` |
| `temperature_min_c`, `temperature_max_c`, `temperature_mean_c` | NUMERIC(6,2) | IMD min/max; NASA `T2M` → mean |
| `relative_humidity_pct` | NUMERIC(6,2) | NASA `RH2M` |
| `source` | VARCHAR(64) | `nasa_power` \| `imd` |
| `provenance` | JSONB | API params, lat/lon, `imd_obj_id`, departure fields |
| `observed_at`, `ingested_at` | TIMESTAMPTZ | Source observation time vs ingest time |
| `supersedes_id`, `validation_status` | UUID, enum | Reuses `observation_validation_status` from 0005 |

**Partitioning:** `weather_observation_2026_06` + `weather_observation_default` (same ops playbook as price/arrival).

**Indexes:** `(region_id, as_of_date DESC)`, `(commodity_id, as_of_date DESC)`, `(source, as_of_date)`.

---

## 3. Deliverables

| Artifact | Path |
|----------|------|
| Migration | `backend/app/persistence/migrations/versions/0009_weather_observations.py` |
| ORM | `backend/app/persistence/models/weather.py` |
| Repository | `backend/app/persistence/repositories/weather.py` |
| Validation | `backend/app/persistence/validation/weather.py` |
| UoW wiring | `backend/app/persistence/unit_of_work.py` → `weather_observations` |
| Tests | `tests/unit/test_weather_observations.py` |

---

## 4. Tests

| Test | Type | Notes |
|------|------|-------|
| `test_weather_source_rejects_invalid` | Unit | No DB |
| `test_weather_source_accepts_nasa_power_and_imd` | Unit | No DB |
| `test_weather_observation_append_only` | Integration | `DATABASE_URL` |
| `test_weather_observation_invalid_region_fk` | Integration | `DATABASE_URL` |
| `test_weather_observation_repository_rejects_invalid_source` | Integration | `DATABASE_URL` |
| `test_weather_partition_parent_present` | Integration | `DATABASE_URL` |
| `test_alembic_revision_chain_linear` | Unit | Head `0009_weather_observations` |

**Unit test count (no DB):** 2  
**Total tests in module:** 6 (4 integration when `DATABASE_URL` set)

---

## 5. Quality Gates

| Tool | Result |
|------|--------|
| `ruff check` / `ruff format` (changed paths) | **Pass** |
| `mypy` (`models/weather.py`, `repositories/weather.py`, `validation/weather.py`, `unit_of_work.py`) | **Pass** |
| `pytest tests/unit/test_weather_observations.py tests/unit/test_alembic_revision_chain.py -m "not integration"` | **4 passed** |
| `pytest … -m integration` @ `127.0.0.1:5433` | **6 passed** (4 weather + 2 alembic) |
| `alembic upgrade head` | **Pass** — head `0009_weather_observations` |

---

## 6. E-03 Follow-ups (not in this track)

| ID | Action |
|----|--------|
| WS-01 | IMD API key + whitelist → PRIMARY daily ingest |
| WS-02 | Map `OBJ_ID` into `region.external_refs` |
| WS-05 | 36–60 mo NASA POWER backfill into `weather_observation` |
| W-3 | Production ingest job (no scheduler in PI6-C) |

NASA POWER spike client (`backend/app/spike/weather/nasa_power.py`) remains non-production; E-03 should map `NasaPowerDailyPoint` → `WeatherObservationModel` rows.

---

## 7. Reference Return Values

| Field | Value |
|-------|-------|
| Migration revision | `0009_weather_observations` |
| Model path | `backend/app/persistence/models/weather.py` |
| Test count | 6 (`tests/unit/test_weather_observations.py`) |
| Report path | `docs/reviews/WEATHER_PERSISTENCE_REPORT.md` |

---

*End of weather persistence report — PI6 Track C.*
