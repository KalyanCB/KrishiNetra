# Cotton Lifecycle Signal Mapping — Phase 1

**Date:** 2026-06-04  
**PI:** PI2 Track D (KDO rerun — Agent 4)  
**Input:** [COMMODITY_LIFECYCLE_MODEL.md](./COMMODITY_LIFECYCLE_MODEL.md), [WEATHER_SIGNAL_FRAMEWORK.md](./WEATHER_SIGNAL_FRAMEWORK.md), [PROCUREMENT_SIGNAL_MODEL.md](./PROCUREMENT_SIGNAL_MODEL.md)  
**Status:** Research — informs agents/features; no schema change, no new requirements

---

## 1. Purpose

Map cotton lifecycle stages to **weather**, **market**, and **policy** signal interpretation for Phase 1 agents. Supports phase-aware features and confidence (no future leakage per TDS-006 §5, TDS-007 §8.6).

This document does **not** define schema or registry fields — it informs E-02 registry seed, E-03 ingest calendars, and E-05 agent phase gates.

---

## 2. Lifecycle Overview (Cotton, India)

```mermaid
flowchart LR
  S[Sowing May–Jul] --> G[Growth Aug–Sep]
  G --> H[Harvest Oct–Feb]
  H --> A[Arrivals Oct–Mar]
  A --> ST[Storage Nov–Jun]
  ST --> M[Clearance rolling]
```

| Phase | Months (indicative) | Primary observation types |
|-------|---------------------|----------------------------|
| Sowing | May–Jul | Rainfall, soil moisture, acreage stats |
| Growth | Aug–Sep | Monsoon peak, boll fill, drought indices |
| Harvest | Oct–Feb (north→south) | Pick rate, dry spells, arrival onset |
| Arrivals | Oct–Mar | Mandi volume spike, modal price |
| Storage | Nov–Jun | Humidity, carry cost, ginning lag |
| Clearance | Rolling | Export demand, futures curve, global inventories |

**Registry link:** Cotton `weather_variables[]` should list rainfall, humidity, acreage (COMMODITY_LIFECYCLE_MODEL §3).

---

## 3. Lifecycle → Signal Interpretation Matrix

| Stage | Weather signal | Market signal | Policy signal |
|-------|----------------|---------------|---------------|
| **Sowing** (May–Jul) | Bullish if drought limits acreage (`acreage_proxy_pct_change` ↓); bearish if excess pre-monsoon rain delays planting | Low mandi volume — **arrival z-scores not meaningful**; price trend low signal-to-noise | MSP announce → step-change in Policy `msp_inr_quintal`; CCI window planning — `cci_active_procurement` typically false |
| **Growth** (Aug–Sep) | Excess rain → bearish quality/magnitude (`rainfall_anomaly_30d`); drought index → bullish supply fear | Early price drift; arrivals minimal | Policy low relevance unless export restriction event |
| **Harvest** (Oct–Feb) | Dry harvest window → favorable `harvest_window_score` (bearish near-term supply pressure); rain at pick → bearish quality | Arrival ramp begins — **arrival z-score activating**; modal price volatility | MSP proximity computed vs Agmarknet modal; Decision `near_msp` uses ±3% rule (TDS-008) |
| **Arrivals peak** (Oct–Mar) | Post-harvest humidity → `storage_humidity_risk` | **Primary Market agent season** — mandi modal, volume spike, regional strength | Active CCI buying → floor support (Policy bullish); procurement volume MTD in components |
| **Storage** (Nov–Jun) | Humidity/unseasonal rain → bearish quality/storage | Carry / basis vs NCDEX KAPAS (Futures agent when licensed); price carry | Procurement volume updates Policy confidence; MSP revision rare mid-season |
| **Clearance** (rolling) | Less weather-sensitive | Export demand, regional strength, clearance pricing | PIB events; MSP revision rare |

---

## 4. Critical Rain Windows → Signal Impact

From COMMODITY_LIFECYCLE_MODEL §3 and WEATHER_SIGNAL_FRAMEWORK §3:

| Window | Calendar | Weather components | Direction bias | Magnitude driver |
|--------|----------|-------------------|----------------|------------------|
| **Boll fill** | Aug–Sep | `rainfall_anomaly_30d`, quality sub-score | Excess rain → **bearish** (micronaire, color downgrade) | Anomaly severity × station coverage |
| **Peak pick** | Oct–Nov (MH, GJ) | `harvest_window_score`, `rainfall_anomaly_7d`, `forecast_rain_3d_mm` | Rain disruption → **bullish** short-term (arrival delays, price spikes) | Forecast accuracy (3d rain) |
| **Post-harvest storage** | Nov–Mar | `storage_humidity_risk` | High humidity → **bearish** (mold, quality loss) | Secondary — lower confidence |

**Rain windows are phase gates:** Weather agent applies stage weights from §6 when computing composite magnitude (see SIGNAL_MATH_SPECIFICATION §4).

---

## 5. Signal Impact Matrix (Agent × Lifecycle Stage)

Legend: **H** = high relevance, **M** = medium, **L** = low, **—** = suppress / do not compute feature

| Agent | Sowing | Growth | Harvest | Arrivals | Storage | Clearance |
|-------|--------|--------|---------|----------|---------|-----------|
| **Market** | L | M | M | **H** | M | **H** |
| **Weather** | **H** | **H** | **H** | M | M | L |
| **Policy** | M | L | M | **H** | **H** | M |
| **Futures** | L | L | M | M | **H** | **H** |
| **Demand** | M | M | L | M | M | **H** |
| **Global** | M | M | L | L | M | **H** |

### 5.1 Market agent by stage

| Stage | Active components | Suppressed |
|-------|-------------------|------------|
| Sowing–Growth | Price trend only (low weight) | `arrival_volume_zscore`, `arrival_trend_14d` |
| Harvest–Arrivals | Price trend + arrival z-score + regional strength | — |
| Storage–Clearance | Price trend + basis (when Futures licensed) + regional strength | Arrival z-score outside peak |

### 5.2 Weather agent by stage

| Stage | Dominant `primary_driver` | Components emphasized |
|-------|---------------------------|----------------------|
| Sowing | `acreage_proxy` | `acreage_proxy_pct_change`, pre-monsoon anomaly |
| Growth | `rainfall_anomaly_30d` | drought index, boll-fill rain |
| Harvest | `harvest_window_score` | 7d/30d anomaly, 3d forecast rain |
| Storage | `storage_humidity_risk` | humidity, unseasonal rain |

### 5.3 Policy agent by stage

| Stage | Dominant components | Decision coupling |
|-------|---------------------|-------------------|
| Sowing | MSP announce events | Registry MSP update |
| Arrivals–Storage | `cci_active_procurement`, `spot_vs_msp_pct`, volume MTD | MSP/CCI floor rule (TDS-008 §5.1) when `near_msp AND cci_active` |
| Clearance | PIB export/procurement events | EXPORT_PUSH regime (TDS-009 §5.1) |

---

## 6. Feature Gating Rules (E-03 / E-05)

| Rule ID | Condition | Action |
|---------|-----------|--------|
| FG-01 | Outside Oct–Mar arrival window | Do not compute `arrival_volume_zscore`, `arrival_trend_14d` |
| FG-02 | Outside May–Jul sowing window | Mask `acreage_proxy_pct_change` or apply L weight only |
| FG-03 | Outside harvest/storage windows | Suppress `harvest_window_score`, `storage_humidity_risk` respectively |
| FG-04 | `futures_feed_ok=false` | Suppress `basis_spot_futures`, `carry_implied_*`; Market agent may use spot-only with confidence penalty (TDS-004 §4.1) |
| FG-05 | All gates | Features at `as_of_date` T use only observations with `observed_at <= T` (TDS-007 §8.6) |

**Forecasting dependency:** Lifecycle-aware masks are **required before credible forecasting** (COMMODITY_LIFECYCLE_MODEL §7). E-01 stores schema only; phase gates implemented in E-03/E-05.

---

## 7. Data Sources by Stage

| Stage | Primary | Secondary |
|-------|---------|-----------|
| Sowing/Growth | IMD, NASA POWER | State acreage stats, USDA India production estimates |
| Harvest/Arrivals | Agmarknet (price, arrivals) | eNAM confirmatory |
| Storage/Price | Agmarknet, NCDEX KAPAS (when licensed per DS-001) | CCI announcements (PIB) |
| Global context | USDA WASDE, ICAC | — |

---

## 8. MI Regime Overlap (TDS-009)

Lifecycle conditions intersect with market regime detection:

| Regime | Lifecycle trigger | Affected agents |
|--------|-------------------|-----------------|
| `TIGHT_SUPPLY` | Arrivals stage + low arrival z-score | Market, Weather |
| `MSP_FLOOR` | Arrivals/Storage + spot within ±3% MSP + CCI active | Policy, Market |
| `CURVE_BACKWARDATION` | Storage/Clearance + steep futures slope | Futures |
| `EXPORT_PUSH` | Clearance + strong export demand signal | Demand, Global |

Regime priority order unchanged from TDS-009 §5.2 (DATA_DEGRADED first).

---

## 9. Regional Notes

| Region | Harvest window | Primary signals |
|--------|----------------|-----------------|
| Telangana (Khammam, Warangal) | Oct–Jan typical | IMD district rain + Agmarknet arrivals/prices |
| Gujarat / Maharashtra | Oct–Nov peak pick rain risk | Same agents; higher `harvest_window_score` weight in registry (LC-01) |
| North (Punjab, Haryana) | Oct–Dec earlier pick | Arrival peak shifts earlier in FG-01 calendar |

---

## 10. Open Items (from lifecycle model)

| ID | Unknown | Impact on mapping |
|----|---------|-------------------|
| LC-01 / LSM-01 | State-level harvest calendar granularity | Weather agent regional weights |
| LC-02 / LSM-02 | Ginning lag between farm-gate and mandi | Arrival vs price lead-lag in Market components |
| LC-03 / LSM-03 | CCI procurement timing vs market floor | Policy agent coupling to Market during Arrivals |

---

## 11. Traceability

| Section | Source |
|---------|--------|
| Lifecycle phases | COMMODITY_LIFECYCLE_MODEL §2–3 |
| Rain windows | COMMODITY_LIFECYCLE_MODEL §3, WEATHER_SIGNAL_FRAMEWORK §3 |
| Policy components | PROCUREMENT_SIGNAL_MODEL §3, TDS-004 §4.3 |
| Feature gating | TDS-007 §5.2, §8.6 |
| Regimes | TDS-009 §5 |

---

*End of cotton lifecycle signal mapping.*
