# Weather Signal Framework — Phase 1 Cotton

**Date:** 2026-06-04  
**Epic:** E-01 Phase 4 (research) / E-03+ (implementation)  
**Status:** Framework doc — no agent code  
**Sources:** TDS-004 §3 (Weather agent), TDS-006 §3.8, TDS-007, founder acreage clarification

---

## 1. Purpose

Distinguish **weather observations** (facts) from **weather signals** (agent outputs), and define candidate Weather agent `signal_components` for cotton harvest, rain, storage, and quality risks.

---

## 2. Observations vs Forecasts vs Signals

| Layer | What it is | Storage (Phase 1) | Consumer |
|-------|------------|-------------------|----------|
| **Observation** | Measured rainfall, temperature, humidity at grid/district | Staging / feature inputs (E-03); not mandi `price_observation` | Weather agent |
| **Forecast** | IMD/NWP predicted rainfall 1–7 days | Agent input only; **not** persisted as StructuredSignal until agent runs | Weather agent |
| **StructuredSignal** | Daily Weather agent output: value, direction, magnitude, confidence | `structured_signal` (agent_type=Weather) | SignalSnapshot → Forecast |

**Rule:** Raw gridded ERA5/IMD rows are **not** StructuredSignals. The Weather agent aggregates observations + short forecasts into one daily signal per TDS-004.

---

## 3. Cotton-Specific Weather Risks

| Risk window | Calendar (India cotton) | Weather driver | Signal relevance |
|-------------|-------------------------|----------------|------------------|
| Sowing / germination | Jun–Jul (kharif) | Pre-monsoon rain, soil moisture | Acreage / early-season bias (acreage in `signal_components`) |
| Growth / boll development | Aug–Sep | Excess rain → pest, quality | Bearish quality component |
| Harvest / picking | Oct–Feb (regional spread) | Clear dry spells favor picking | Bullish harvest progress |
| Post-harvest / storage | Nov–Mar | Humidity, unseasonal rain | Storage loss risk → bearish |
| Quality (micronaire, color) | Harvest period | Rain at pick → quality downgrade | Magnitude on quality sub-component |

---

## 4. Candidate Signal Definitions

Weather agent produces **one** StructuredSignal per day; sub-risks live in `signal_components`:

```json
{
  "rainfall_anomaly_7d": -0.15,
  "rainfall_anomaly_30d": 0.08,
  "drought_index": 0.22,
  "harvest_window_score": 0.71,
  "storage_humidity_risk": 0.35,
  "acreage_proxy_pct_change": -0.02,
  "forecast_rain_3d_mm": 12.5,
  "primary_driver": "harvest_window"
}
```

| Component | Direction impact | Confidence driver |
|-----------|------------------|-------------------|
| `rainfall_anomaly_*` | Excess rain near harvest → bearish | Station density, IMD lag |
| `drought_index` | Severe deficit → bullish price (supply) | Regional coverage |
| `harvest_window_score` | Favorable dry spell → bearish near-term pressure | Forecast accuracy |
| `storage_humidity_risk` | High humidity → bearish quality | Secondary |
| `acreage_proxy_pct_change` | Lower acreage → bullish (founder: in Weather signal) | USDA/state stats lag |

Top-level signal fields (TDS-004 contract):

- `value`: composite score (e.g. normalized supply pressure from weather)
- `direction`: bullish / bearish / neutral vs baseline
- `magnitude`: strength of weather impact [0, 1]
- `confidence`: data completeness × forecast horizon penalty

---

## 5. Data Sources (Observations)

| Source | Variables | Cadence | Phase 1 role |
|--------|-----------|---------|--------------|
| **IMD** | District rainfall, warnings | Daily | Primary India rainfall |
| **NASA POWER** | Grid rainfall, temp, humidity | Daily | Gap-fill / historical backfill |
| **State ag stats** | Acreage reports | Seasonal | `acreage_proxy` in components |

Weather is **optional** agent in cotton registry (TDS-009); missing → confidence penalty, not pipeline abort.

---

## 6. Predictive Value Assessment

| Question | Assessment |
|----------|------------|
| Is weather predictive for cotton price? | **Yes, conditionally** — harvest rain and acreage affect supply timing and quality; effect lags 2–8 weeks |
| Phase 1 minimum | 36 months historical regional aggregates for seasonal features |
| Blockers | IMD IP whitelist; acreage from non-IMD sources |

---

## 7. Open Questions

| ID | Item |
|----|------|
| WQ-01 | Grid → cotton-belt aggregation weights (state vs district) |
| WQ-02 | ERA5 vs IMD precedence for backfill |
| WQ-03 | Forecast horizon cap before confidence decay |

---

*End of weather signal framework.*
