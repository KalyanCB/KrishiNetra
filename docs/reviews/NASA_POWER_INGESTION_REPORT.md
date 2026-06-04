# NASA POWER Weather Ingestion Report — PI6 Track D

**Date:** 2026-06-04  
**PI:** PI6 Track D (KDO — E-03 NASA POWER ingest)  
**Status:** Production ingest complete — append-only `weather_observation`; no Weather agent / signals  
**Strategy baseline:** [WEATHER_DATA_STRATEGY_V1.md](../research/WEATHER_DATA_STRATEGY_V1.md)  
**Spike baseline:** [WEATHER_SPIKE_REPORT.md](./WEATHER_SPIKE_REPORT.md)  
**Persistence baseline:** [WEATHER_PERSISTENCE_REPORT.md](./WEATHER_PERSISTENCE_REPORT.md)

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| NASA POWER rows persisted? | **Yes** — 5,620 rows @ `127.0.0.1:5433` after 36-mo backfill |
| Telangana cotton belt covered? | **Yes** — 5 districts / region_ids |
| Rainfall + temperature validated? | **Yes** — `validate_rainfall_mm`, `validate_temperature_mean_c` |
| Append-only repository? | **Yes** — `WeatherObservationRepository` + business-key dedupe |
| Signal generation? | **No** — out of scope |

**Overall:** **PASS** — closes WS-05 backfill path for dev/backtest bootstrap.

---

## 2. Targets and Mapping

| District | Centroid (lat/lon) | `region_id` | Rows (36-mo backfill) |
|----------|-------------------|-------------|------------------------|
| Khammam | 17.25, 79.75 | `reg_tg_khammam` | 1,124 |
| Warangal | 17.97, 79.59 | `reg_tg_warangal` | 1,124 |
| Karimnagar | 18.44, 79.13 | `reg_tg_karimnagar` | 1,124 |
| Nalgonda | 17.05, 79.27 | `reg_tg_nalgonda` | 1,124 |
| Mahabubabad | 17.60, 80.00 | `reg_tg_mahabubabad` | 1,124 |

**Commodity:** `cotton` (E-02 seed applied idempotently before ingest).

**Window (default CLI):** `2023-05-01` → `2026-05-31` (36 calendar months, end = today − 4 days per spike T−4 lag).

---

## 3. Deliverables

| Artifact | Path |
|----------|------|
| Ingest service | `backend/app/services/ingest/weather/` |
| Field validation | `backend/app/persistence/validation/weather.py` |
| Cotton seed extension | `backend/app/persistence/seeds/fixtures/cotton.json` (`reg_tg_nalgonda`, `reg_tg_mahabubabad`) |
| CLI | `scripts/nasa_power_ingest.py` |
| Unit / integration tests | `tests/unit/test_nasa_power_ingest.py` |
| NASA POWER client (reused) | `backend/app/spike/weather/nasa_power.py` |

---

## 4. Ingest Run (@ 5433)

```bash
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  .venv/bin/python scripts/nasa_power_ingest.py --months 36
```

| Metric | Value |
|--------|-------|
| Points fetched | 5,620 |
| Rows persisted (run) | 5,618 |
| Skipped duplicate | 2 |
| `nasa_power` rows after run | **5,620** |

---

## 5. Tests

| Module | Unit (no DB) | Integration (`DATABASE_URL`) | Total |
|--------|--------------|------------------------------|-------|
| `test_nasa_power_ingest.py` | 6 | 3 | **9** |
| `test_weather_observations.py` (+ rainfall/temp validators) | 3 | 4 | 7 |

**Track D ingest tests:** 9 in `tests/unit/test_nasa_power_ingest.py` (includes optional live NASA call).

---

## 6. Quality Gates

| Tool | Result |
|------|--------|
| `ruff check` / `ruff format` (ingest + validation + script + tests) | **Pass** |
| `mypy` (`backend/app/services/ingest/weather`, `validation/weather.py`) | **Pass** |
| `pytest tests/unit/test_nasa_power_ingest.py tests/unit/test_weather_observations.py -m "not integration"` | **Pass** |
| `pytest …` @ `127.0.0.1:5433` (integration) | **Pass** |

---

## 7. CLI Usage

```bash
# Default 36-month backfill
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  .venv/bin/python scripts/nasa_power_ingest.py

# Custom window
.venv/bin/python scripts/nasa_power_ingest.py --start 2022-06-01 --end 2025-05-31

# Dry-run (fetch + dedupe, rollback)
.venv/bin/python scripts/nasa_power_ingest.py --months 12 --dry-run
```

---

## 8. Reference Return Values

| Field | Value |
|-------|-------|
| Script path | `scripts/nasa_power_ingest.py` |
| Rows persisted (36-mo @ 5433) | **5,620** |
| Report path | `docs/reviews/NASA_POWER_INGESTION_REPORT.md` |
| Test count (`test_nasa_power_ingest.py`) | **9** |

---

*End of NASA POWER ingestion report — PI6 Track D.*
