# E-03 Parallel Completion Status — PI9 Track F

**Date:** 2026-06-04  
**PI:** PI9 Track F (KDO — E-03 parallel, non-blocking to E-04)  
**Workspace:** `e9fa355`  
**Scope:** Documentation + minimal wiring only — no heavy backfill, no signal runtime

---

## 1. Executive summary

| Item | Status |
|------|--------|
| **E-04** | **Not blocked** — degraded agent wiring may proceed independently |
| **OGD live backfill** | **OPEN** — `OGD_API_KEY` not registered in ops env |
| **Belt market coverage** | **18 / 27** reporting (fixture); **9 / 27** fixture-empty |
| **Agmarknet validation** | **CLOSED** (PI8) — price/arrival promoted `received` → `validated` |
| **Weather validation** | **GAP** — **5,620** NASA POWER rows remain `received`; batch path added (optional run) |

---

## 2. OGD_API_KEY onboarding

| Check | Status |
|-------|--------|
| `Settings.ogd_api_key` | Wired (`backend/app/config/settings.py`) |
| `.env.example` onboarding steps | **Documented** (PI9 — register at data.gov.in, live backfill commands) |
| Key in local `.env` / shell | **Absent** (ops) |
| Demo / placeholder key | **`Key not authorised`** — wire-format only |
| CLI without key | `OGD_API_KEY required for live backfill (or use --fixture)` |

### 2.1 Ops steps (ordered)

1. Register at [data.gov.in](https://www.data.gov.in) → **My Account** → API key ([OGD Help](https://www.data.gov.in/help)).
2. Set `OGD_API_KEY` in `.env` (never commit). See `.env.example` comments.
3. Live belt backfill @ integration DB:

```bash
export DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra
export OGD_API_KEY='<registered-key>'

uv run python scripts/agmarknet_backfill.py \
  --scope belt --months 36
```

4. Refresh coverage stats: `uv run python scripts/agmarknet_backfill.py --stats --write-report --scope belt`.
5. Optional: OGD catalog zip bulk per [AGMARKNET_PRODUCTION_ONBOARDING.md](../research/AGMARKNET_PRODUCTION_ONBOARDING.md).

**Runbook:** [AGMARKNET_PRODUCTION_ONBOARDING.md](../research/AGMARKNET_PRODUCTION_ONBOARDING.md) · **Gap analysis:** [OBSERVATION_COVERAGE_GAPS.md](../research/OBSERVATION_COVERAGE_GAPS.md) §6

---

## 3. Nine empty belt mandis (fixture)

Source: [MARKET_COVERAGE_IMPROVEMENT.md](./MARKET_COVERAGE_IMPROVEMENT.md) §4.1 — seeded in E-02, no price rows after belt fixture replay.

| # | `market_id` | State |
|---|-------------|-------|
| 1 | `mkt_tg_adilabad` | Telangana |
| 2 | `mkt_tg_jagtial` | Telangana |
| 3 | `mkt_tg_mancherial` | Telangana |
| 4 | `mkt_tg_nalgonda` | Telangana |
| 5 | `mkt_tg_peddapalli` | Telangana |
| 6 | `mkt_mh_jalgaon` | Maharashtra |
| 7 | `mkt_mh_parbhani` | Maharashtra |
| 8 | `mkt_mh_latur` | Maharashtra |
| 9 | `mkt_gj_surendranagar` | Gujarat |

**Unblock:** Additional fixture tuples in `tests/fixtures/agmarknet/ogd_cotton_belt_sample.json` **or** live OGD pull after `OGD_API_KEY` registration.

---

## 4. Weather validation lifecycle gap

| Question | Answer |
|----------|--------|
| Are weather rows still `received`? | **Yes** — all **5,620** `weather_observation` rows (cotton, `nasa_power`) @ 5433 |
| Ingest-time field checks? | **Yes** — `backend/app/persistence/validation/weather.py` at repo insert |
| Post-ingest batch promotion? | **Was missing** — Agmarknet-only `ObservationValidationService` (PI8 Track A) |
| DQS impact | Non-`validated` rows count as anomalies → weather tier penalty **~0.30** (capped); blended score ceiling ~**0.71** vs Agmarknet-only ~**0.85** |

### 4.1 Lifecycle (intended)

```
ingest (NASA POWER) → received (draft)
       → validated (batch QA) → published (future)
```

Agmarknet path: `scripts/observation_validate.py` after backfill ([OBSERVATION_VALIDATION_REPORT.md](./OBSERVATION_VALIDATION_REPORT.md)).

Weather path (PI9 parallel): `WeatherObservationValidationService` — optional `--include-weather` on the same CLI:

```bash
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/observation_validate.py --include-weather
```

No automatic cron; ops-run when clearing weather DQS penalty. **Does not block E-04.**

---

## 5. Deliverables (this track)

| Artifact | Path |
|----------|------|
| **This report** | `docs/reviews/E03_PARALLEL_STATUS.md` |
| OGD onboarding in env template | `.env.example` |
| Weather batch validator (parallel) | `backend/app/services/validation/weather_observation_validation_service.py` |
| Agmarknet batch validator (existing) | `backend/app/services/validation/observation_validation_service.py` |

---

## 6. Explicit non-goals (PI9 F)

- Heavy live OGD backfill or 90-day production audit
- Signal runtime / E-04 agent execution
- IMD PRIMARY weather tier
- Fixture expansion for nine mandis (Track E follow-up)

---

## 7. References

| Doc | Role |
|-----|------|
| [MARKET_COVERAGE_IMPROVEMENT.md](./MARKET_COVERAGE_IMPROVEMENT.md) | 18/27 coverage, nine empty mandis |
| [QUALITY_IMPROVEMENT_REPORT.md](./QUALITY_IMPROVEMENT_REPORT.md) | Weather `received` + DQS blend |
| [WEATHER_ACTIVATION_REPORT.md](./WEATHER_ACTIVATION_REPORT.md) | NASA POWER ingest @ 5433 |
| [E03_S02_COMPLETION_REPORT.md](./E03_S02_COMPLETION_REPORT.md) | Fixture backfill baseline |

---

*End of PI9 Track F E-03 parallel status.*
