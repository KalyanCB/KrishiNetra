# Historical Agmarknet Backfill Report — PI6 Track B

**Date:** 2026-06-04  
**PI:** PI6 Track B (KDO — Telangana cotton mandi historical backfill)  
**Status:** Backfill framework complete — production pipeline + date-window OGD  
**Seed:** E-02 `cotton.json` (4 Telangana mandis with `source_identifiers.agmarknet`)

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Backfill framework shipped? | **Yes** — `backfill.py`, CLI, partition migration `0010`, unit tests |
| Target window | **36 calendar months** default (`2023-06-01` → yesterday); **24 mo minimum** supported via `--months 24` |
| Seed markets | **4** — Khammam, Warangal, Karimnagar, Kesamudram |
| Production pipeline reused? | **Yes** — `AgmarknetIngestPipeline` parse → map → dedupe → persist |
| Partition G7 (multi-month DDL)? | **Yes** — `0010_observation_partitions_backfill` (2023-06 … 2026-12, skips existing `2026_06`) |
| Live national corpus loaded? | **Ops** — requires `OGD_API_KEY` and per-day API pulls (or zip bulk per onboarding runbook) |

**Overall:** **PASS** (framework) — closes PI6 Track B engineering path; live row counts are environment-dependent.

---

## 2. Window and Coverage (framework defaults)

| Metric | Value |
|--------|-------|
| Default start (36 mo) | `2023-06-01` |
| Default end | Yesterday (inclusive) |
| OGD filter | `state=Telangana`, `arrival_date=DD/MM/YYYY` per day |
| Mapper | Cotton labels only; unknown mandis skipped |

### Per-market (seed)

| `market_id` | Agmarknet triple |
|-------------|------------------|
| `mkt_tg_khammam_apmc` | Telangana / Khammam / Khammam |
| `mkt_tg_warangal` | Telangana / Warangal / Warangal |
| `mkt_tg_karimnagar` | Telangana / Karimnagar / Karimnagar |
| `mkt_tg_kesamudram` | Telangana / Khammam / Kesamudram |

---

## 3. Deliverables

| Artifact | Path |
|----------|------|
| Backfill service | `backend/app/services/ingest/agmarknet/backfill.py` |
| Partition migration | `backend/app/persistence/migrations/versions/0010_observation_partitions_backfill.py` |
| CLI | `scripts/agmarknet_backfill.py` |
| Unit tests | `tests/unit/test_agmarknet_backfill.py` |
| Fixture (CI replay) | `tests/fixtures/agmarknet/ogd_telangana_sample.json` |

---

## 4. CLI

```bash
# Fixture dry-run (no API key)
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5432/krishinetra \
  uv run python scripts/agmarknet_backfill.py --fixture --dry-run

# Live 36-month window
DATABASE_URL=... OGD_API_KEY=... \
  uv run python scripts/agmarknet_backfill.py --start-date 2023-06-01 --end-date 2026-06-03

# Stats + refresh this report
uv run python scripts/agmarknet_backfill.py --stats --write-report \
  --start-date 2023-06-01 --end-date 2026-06-03
```

---

## 5. Tests

| Module | Unit (no DB) | Integration (`DATABASE_URL`) |
|--------|--------------|------------------------------|
| `test_agmarknet_backfill.py` | 10 | 1 (optional @ 5433) |

---

## 6. Reproducibility

- Deterministic date iteration (`iter_backfill_dates`).
- Business-key dedupe via production `AgmarknetIngestPipeline`.
- CI: `--fixture` replays `ogd_telangana_sample.json` with per-day `arrival_date` stamping.
- Live: registered `OGD_API_KEY`; idempotent re-runs skip duplicates.

---

## 7. Fixture proof (@ unit / integration)

| Metric | Fixture single-day (`2022-03-26`) |
|--------|-------------------------------------|
| OGD rows / day | 4 (sample fixture) |
| Markets with cotton rows | ≥ 1 (Khammam + Warangal in sample) |
| Idempotent re-run | `total_inserted=0`, duplicates skipped |

Refresh live metrics with `--stats --write-report` after production backfill.
