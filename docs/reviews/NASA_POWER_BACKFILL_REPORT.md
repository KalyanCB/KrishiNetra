# NASA POWER Historical Weather Backfill Report — PI7 Track D

**Date:** 2026-06-04  
**PI:** PI7 Track D (KDO — NASA POWER historical weather backfill)  
**Status:** Backfill complete @ `127.0.0.1:5433` — 5,620 rows, 36 calendar months  
**Prerequisites:** Migration `0009` / `0010` @ head; `WeatherObservationRepository` (PI6 Track C)  
**Prior ingest report:** [NASA_POWER_INGESTION_REPORT.md](./NASA_POWER_INGESTION_REPORT.md)  
**Strategy:** [WEATHER_DATA_STRATEGY_V1.md](../research/WEATHER_DATA_STRATEGY_V1.md)

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Row count @ 5433 | **5,620** (`source = nasa_power`) |
| Date span | **2023-05-01** → **2026-05-31** (inclusive) |
| Belt regions covered | **5 / 5** — Khammam, Warangal, Karimnagar, Nalgonda, Mahabubabad |
| ≥ 24 months per belt region? | **Yes** — 758 rows each in rolling 24-mo window (761 calendar days; 99.6%) |
| Rainfall + temperature validated? | **Yes** — mapper + DB audit; 0 null / 0 out-of-range |
| Re-run required? | **Yes** (this session) — DB had **0** rows before backfill; ingest restored PI6 target |
| Signal runtime | **No** — ingest + persistence only |

**Overall:** **PASS** — historical bootstrap ready for backtest / DQS weather merge.

---

## 2. Pre-Backfill Verification (@ 5433)

| Check | Result |
|-------|--------|
| Alembic head | `0010_partition_backfill` |
| `weather_observation` table | Present (+ monthly partitions) |
| NASA POWER rows before run | **0** |
| Cotton `region` rows before run | **0** (seed applied by ingest pipeline) |

**Blockers resolved:**

1. **Empty dev DB** — no NASA POWER rows; `scripts/nasa_power_ingest.py` applied cotton seed and persisted full window in one run.  
2. **`RegistryService` class cache** — cached `CommodityRegistryModel` from a closed session caused `DetachedInstanceError` in `record_after_weather_ingest` on integration re-runs; fixed by re-fetching when `object_session(cached.config) is not self._session`.

---

## 3. Backfill Run

```bash
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  .venv/bin/python scripts/nasa_power_ingest.py --months 36
```

| Metric | Value |
|--------|-------|
| Window start | `2023-05-01` |
| Window end | `2026-05-31` (today − 4 days, NASA POWER T−4 lag) |
| Points fetched | 5,620 |
| Rows persisted | 5,620 |
| Skipped duplicate | 0 |
| Rows after run | **5,620** |

---

## 4. Coverage by Region

NASA POWER ingest targets **Telangana cotton belt centroids** (`TELANGANA_COTTON_DISTRICTS` → `DISTRICT_REGION_IDS`). These are the weather-backed districts in E-02 seed; other cotton seed regions (e.g. `reg_tg_kesamudram`, `reg_tg_state`) are market hierarchy nodes without daily gridded pulls.

| District | `region_id` | Total rows | Min date | Max date | Rows in 24-mo window* |
|----------|-------------|------------|----------|----------|------------------------|
| Khammam | `reg_tg_khammam` | 1,124 | 2023-05-01 | 2026-05-31 | 758 |
| Warangal | `reg_tg_warangal` | 1,124 | 2023-05-01 | 2026-05-31 | 758 |
| Karimnagar | `reg_tg_karimnagar` | 1,124 | 2023-05-01 | 2026-05-31 | 758 |
| Nalgonda | `reg_tg_nalgonda` | 1,124 | 2023-05-01 | 2026-05-31 | 758 |
| Mahabubabad | `reg_tg_mahabubabad` | 1,124 | 2023-05-01 | 2026-05-31 | 758 |

\*24-mo window: `2024-05-01` → `2026-05-31` (761 inclusive calendar days). Three missing days per region vs. full calendar (likely API edge / lag); **exceeds 24-month minimum**.

**Commodity:** `cotton` on all rows.

---

## 5. Rainfall and Temperature Validation

### 5.1 Ingest-time (mapper)

`map_nasa_power_point` calls:

- `validate_rainfall_mm` — required, `≥ 0`, cap **500 mm**/day  
- `validate_temperature_mean_c` — required, **[-5, 55] °C** (NASA POWER `T2M` → `temperature_mean_c`)

Source: `backend/app/persistence/validation/weather.py`, `backend/app/services/ingest/weather/mapper.py`.

### 5.2 Post-persist audit (@ 5433)

| Field | Rows | Nulls | Range (observed) | Avg |
|-------|------|-------|------------------|-----|
| `rainfall_mm` | 5,620 | 0 | 0.0 – 108.77 mm | 2.92 mm |
| `temperature_mean_c` | 5,620 | 0 | 15.93 – 38.73 °C | 27.56 °C |

| Rule | Result |
|------|--------|
| Negative rainfall | **0** |
| Null rainfall / temperature | **0** |
| Values outside validator caps | **0** (enforced at map time) |

**Interpretation:** Distributions are plausible for Telangana cotton belt (monsoon peaks in rainfall; mean temps in mid-20s °C). No corrective re-ingest required.

---

## 6. Quality Gates

| Tool | Scope | Result |
|------|-------|--------|
| `ruff check` / `ruff format --check` | ingest + validation + script + tests | **Pass** |
| `mypy` | `backend/app/services/ingest/weather`, `validation/weather.py`, script | **Pass** |
| `pytest -m "not integration"` | `test_nasa_power_ingest.py`, `test_weather_observations.py` | **10 passed** |
| `pytest` (with `DATABASE_URL` @ 5433) | same modules | **16 passed** (incl. live NASA day) |

---

## 7. Reference Return Values (PI7 Track D)

| Field | Value |
|-------|-------|
| Row count | **5,620** |
| Regions covered | **5** belt `region_id`s (see §4) |
| Date span | **2023-05-01** → **2026-05-31** |
| Report path | `docs/reviews/NASA_POWER_BACKFILL_REPORT.md` |
| CLI | `scripts/nasa_power_ingest.py` |

---

## 8. Ops Notes

- **Idempotent re-run:** Duplicate business keys skipped via `filter_new_weather_drafts`; safe to re-run same window.  
- **Minimum 24 months only:** `uv run python scripts/nasa_power_ingest.py --months 24`  
- **DQS:** Ingest triggers `DataQualitySnapshotService.record_after_weather_ingest` (Track E).  
- **Out of scope:** Weather agent, `structured_signal`, IMD tier.

---

*End of NASA POWER backfill report — PI7 Track D.*
