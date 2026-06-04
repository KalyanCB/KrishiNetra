# Weather Ingestion Spike Report — PI5 Track D

**Date:** 2026-06-04  
**PI:** PI5 Track D (KDO — proof-of-access spike)  
**Status:** Spike complete — no production ingest, no scheduler, no Weather agent  
**Strategy baseline:** [WEATHER_DATA_STRATEGY_V1.md](../research/WEATHER_DATA_STRATEGY_V1.md)  
**HEAD:** `faf3e66` @ `main`

---

## 1. Executive Verdict

| Source | Viability | Phase 1 role (unchanged) | Spike evidence |
|--------|-----------|--------------------------|----------------|
| **NASA POWER** | **VIABLE — proven live access** | **SECONDARY** (+ BACKFILL option) | HTTP 200 on all five Telangana cotton district centroids; 36-month pull succeeded |
| **IMD public REST** | **FEASIBLE — access gated** | **PRIMARY** (after onboarding) | HTTP 401 `API key missing` on all three probed endpoints; documented contract matches strategy |

**Recommended tiering (confirms strategy V1):**

| Tier | Source | Rationale |
|------|--------|-----------|
| **PRIMARY** | IMD district/state rainfall API | Official India district semantics (actual/normal/departure); nowcast/warning endpoints for forecast inputs |
| **SECONDARY** | NASA POWER | Immediate dev/unblock; gap-fill when IMD district missing or whitelist pending |
| **BACKFILL** | NASA POWER and/or ERA5 | 36–60 mo regional daily aggregates — NASA POWER validated for 36 mo single-call pull |

---

## 2. Scope and Non-Goals

| In scope | Out of scope (explicit) |
|----------|-------------------------|
| Live NASA POWER proof-of-access for Telangana cotton belt | Production ingest pipeline |
| IMD documented-access feasibility probe | Scheduler / cron jobs |
| Minimal spike module + probe script + unit tests | Weather signal agent / `structured_signal` runtime |
| Comparison vs [WEATHER_DATA_STRATEGY_V1.md](../research/WEATHER_DATA_STRATEGY_V1.md) | ERA5 CDS pull (BACKFILL tier — separate spike) |

---

## 3. Telangana Cotton Belt — Probe Targets

Aligned with [WEATHER_DATA_STRATEGY_V1.md §4](../research/WEATHER_DATA_STRATEGY_V1.md) and E-02 cotton seed districts:

| District | Lat / Lon (centroid) | E-02 seed region | NASA POWER (2026-06-04 spike) |
|----------|----------------------|------------------|-------------------------------|
| Khammam | 17.25, 79.75 | `reg_tg_khammam` | HTTP 200 — 7-day series returned |
| Warangal | 17.97, 79.59 | `reg_tg_warangal` | HTTP 200 |
| Karimnagar | 18.44, 79.13 | `reg_tg_karimnagar` | HTTP 200 |
| Nalgonda | 17.05, 79.27 | (strategy list) | HTTP 200 |
| Mahabubabad | 17.60, 80.00 | (strategy list) | HTTP 200 |

**Grid resolution note:** Khammam and Mahabubabad returned identical daily values on 2024-06-01 and in the 7-day probe — expected at NASA POWER ~0.5° resolution; E-03 regional rollup must not treat adjacent districts as independent station observations.

**IMD OBJ_ID mapping:** Not verified in this spike (API blocked). Strategy requires confirming `OBJ_ID` per district via `districtrainfall` after key issuance; sample documented OBJ_ID `164` (Adilabad) used for probe path only.

---

## 4. Live Access Evidence

### 4.1 NASA POWER — verified 2026-06-04

**Endpoint:** `GET https://power.larc.nasa.gov/api/temporal/daily/point`  
**Parameters:** `PRECTOTCORR`, `T2M`, `RH2M`; `community=AG`; JSON format  
**Auth:** None

| Test | Result |
|------|--------|
| Single day (Khammam, 2024-06-01) | HTTP 200 in ~1.1 s; `PRECTOTCORR=0.0`, `T2M=32.77`, `RH2M=64.15` |
| Five-district same-day probe | All HTTP 200; latency 0.46–1.09 s per request |
| 36-month window (2022-06-01 → 2025-05-31) | HTTP 200 in ~1.4 s; **1,096 daily rows**; ~54 KB JSON |
| Latest-available probe | Most recent valid day **2026-05-31** on spike date 2026-06-04 → **T−4 latency** |

Sample 7-day Khammam pull (via `scripts/weather_spike_probe.py`):

```json
{
  "date": "2026-05-31",
  "precipitation_mm": 3.28,
  "temperature_c": 35.38,
  "relative_humidity_pct": 43.51
}
```

### 4.2 IMD — feasibility-only 2026-06-04

**Endpoints probed:**

| Endpoint | URL | Result |
|----------|-----|--------|
| District rainfall | `https://api.imd.gov.in/api/v1/districtrainfall` | HTTP **401** — `{"error":"API key missing"}` |
| District by id | `.../districtrainfall?id=164` | HTTP **401** — same |
| State rainfall | `https://api.imd.gov.in/api/v1/staterainfall` | HTTP **401** — same |

**Interpretation:** IMD public REST remains the correct PRIMARY path per strategy, but production ingest is **blocked until API key + IP whitelist** onboarding ([IMD APIs portal](https://mausam.imd.gov.in/responsive/apis.php)). The 401 response confirms the service is reachable; it does not invalidate feasibility — it validates the onboarding gate documented in [IMD_FEASIBILITY_ASSESSMENT.md](../research/IMD_FEASIBILITY_ASSESSMENT.md).

**Expected IMD record shape** (from research — not re-fetched live):

```json
{
  "OBJ_ID": "164",
  "District": "ADILABAD",
  "Date": "2023-01-31",
  "Daily Actual": "0.00",
  "Daily Normal": "1.70",
  "Daily Departure Per": "-100%",
  "Daily Category": "NR"
}
```

---

## 5. Source Comparison — NASA POWER vs IMD

Synthesized from live spike + [WEATHER_DATA_STRATEGY_V1.md §2](../research/WEATHER_DATA_STRATEGY_V1.md).

| Criterion | NASA POWER | IMD public REST |
|-----------|------------|-----------------|
| **Coverage (Telangana cotton belt)** | **Full** — any lat/lon; 5/5 districts returned data | **Full (district-level)** — all Indian admin districts when authenticated |
| **Spatial semantics** | ~0.5° gridded point; no district departure/category | **District actual / normal / departure / category** — matches DD-002 |
| **Latency (daily ops)** | **T−4 observed** (2026-05-31 latest on 2026-06-04); strategy cites T+2–3 d | **Same-day / daily** operational tier (when whitelisted) |
| **Historical depth (free)** | **1981–present**; 36 mo = single ~54 KB / ~1.4 s call | **Shallow on public API**; deep history via IMD-DSP (commercial gate) |
| **Forecast / nowcast** | **No** | **Yes** — district nowcast/warning endpoints (documented) |
| **Auth / ops complexity** | **Low** — open HTTPS, no key | **Medium** — API key + IP whitelist + attribution; no formal SLA |
| **Commercial clarity** | CC BY 4.0 — open | Grey until legal sign-off; DSP restricted |
| **Spike verdict** | **VIABLE now** | **FEASIBLE after onboarding** |

### Operational complexity summary

| Dimension | NASA POWER | IMD |
|-----------|------------|-----|
| Dev environment | Works immediately | Blocked without key/whitelist |
| Production cron | Simple HTTPS pull per district centroid | Whitelist egress IPs; key rotation; cache on outage |
| Backfill 36 mo | One API call per district (~5 calls → ~270 KB) | Not available on free tier at depth; use BACKFILL tier |
| E-03 mapping | Roll grid to `region` via lat/lon refs | Map `OBJ_ID` → E-02 `region.external_refs` |

---

## 6. Spike Artifacts (non-production)

| Artifact | Purpose |
|----------|---------|
| `backend/app/spike/weather/nasa_power.py` | Minimal NASA POWER daily client |
| `backend/app/spike/weather/imd.py` | IMD access probe (documents 401/200 outcomes) |
| `backend/app/spike/weather/constants.py` | Telangana cotton district centroids + endpoint URLs |
| `scripts/weather_spike_probe.py` | CLI JSON probe (`--source nasa\|imd\|all`) |
| `tests/unit/test_weather_spike.py` | Unit tests (mocked HTTP) + optional live NASA integration test |

**Run probe:**

```bash
.venv/bin/python scripts/weather_spike_probe.py --source all --days 7
```

**Quality gates (spike files):**

| Tool | Result |
|------|--------|
| `pytest tests/unit/test_weather_spike.py -m "not integration"` | 4 passed |
| `ruff check` / `ruff format` | Clean |
| `mypy backend/app/spike/weather` | Clean |

---

## 7. Gaps and E-03 Follow-ups

| ID | Gap | Owner / action |
|----|-----|----------------|
| WS-01 | IMD API key + IP whitelist not issued | Submit onboarding request; store key in secrets manager |
| WS-02 | `OBJ_ID` not mapped in E-02 `external_refs` | Pull district list post-whitelist; extend cotton seed |
| WS-03 | ~0.5° grid collapses adjacent districts | E-03 rollup weights + confidence penalty (WQ-01) |
| WS-04 | NASA POWER lacks departure semantics | Keep IMD PRIMARY for anomaly categories; POWER for gap-fill/backfill |
| WS-05 | 36 mo BACKFILL batch | Schedule one-time POWER pulls per belt region before Weather agent backtest |

---

## 8. Recommendation Summary

| Question | Answer |
|----------|--------|
| Is NASA POWER viable for Telangana cotton? | **Yes** — live access proven; suitable as **SECONDARY** and fast **BACKFILL** |
| Is IMD viable? | **Yes (conditional)** — endpoints reachable; **PRIMARY** after API key + whitelist |
| Change strategy tiering? | **No** — spike confirms PRIMARY=IMD, SECONDARY=NASA POWER, BACKFILL=ERA5 and/or NASA POWER |
| Block E-03? | **No** for weather overall (TDS-009 optional agent) — but IMD PRIMARY cron blocked until WS-01; use NASA POWER for Sprint 0 dev |

---

*End of weather spike report — PI5 Track D.*
