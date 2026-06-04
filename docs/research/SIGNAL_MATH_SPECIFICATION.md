# Signal Math Specification — Phase 1

**Date:** 2026-06-04  
**PI:** PI2 Track E (KDO rerun — Agent 4)  
**Status:** Specification from frozen founder/TDS only — **no implementation, no new requirements**  
**Sources:** TDS-004 §3–§4, TDS-009 §3–§4, TDS-007 §5, TDS-006 §3.8, TDS-008 §5.1, [WEATHER_SIGNAL_FRAMEWORK.md](./WEATHER_SIGNAL_FRAMEWORK.md), [PROCUREMENT_SIGNAL_MODEL.md](./PROCUREMENT_SIGNAL_MODEL.md), [COTTON_LIFECYCLE_SIGNAL_MAPPING.md](./COTTON_LIFECYCLE_SIGNAL_MAPPING.md)

---

## 1. Scope

Defines **Market**, **Weather**, and **Policy** StructuredSignal math: inputs, normalization, direction, magnitude, confidence.

**In scope:** Domain agent internal math producing one StructuredSignal per agent per daily refresh.  
**Out of scope:** MI aggregation (TDS-009), forecast horizons (TDS-007), Decision NHV (TDS-008), Demand/Futures/Global agents (covered in TDS-004 only).

**Prohibited in signal payload:** free text, LLM output (TDS-004, TC-003, TC-004).

---

## 2. Common StructuredSignal Contract

Per TDS-004 §3 (FD-013, REQ-060, REQ-061):

| Field | Type | Range | Rule |
|-------|------|-------|------|
| `agent_type` | enum | Market, Weather, Policy | Required |
| `commodity_id` | id | `cotton` Phase 1 | Required |
| `value` | decimal | Agent-specific normalized strength | Composite score after agent-internal math |
| `direction` | enum | `bullish`, `bearish`, `neutral` | vs baseline / prior regime |
| `magnitude` | decimal | **[0, 1]** | Relative strength (TDS-004 §3) |
| `confidence` | decimal | **[0, 1]** | Data completeness × freshness × horizon penalty |
| `as_of_timestamp` | datetime | — | Data anchor for replay |
| `signal_components` | struct | — | Sub-metrics; traceability only |
| `source_refs[]` | id[] | — | Observation lineage |

**Persistence validation (E-01-S05):** `magnitude`, `confidence` ∈ [0, 1] enforced at repository layer.

**Signed contribution for MI (downstream, E-05):**

\[
s_i = \text{sign}(dir_i) \cdot mag_i \cdot conf_i
\]

where \(dir_i \in \{+1, 0, -1\}\) from bullish/bearish/neutral (TDS-009 §4.2).

---

## 3. Market Signal (AgentType = Market)

**Purpose:** Encode domestic/regional cotton conditions — prices, arrivals, regional strength (TDS-004 §4.1, REQ-050, FD-030).

### 3.1 Inputs

| Input | Source | Observation type |
|-------|--------|------------------|
| Modal/min/max prices | Agmarknet | `PriceObservation[]` |
| Arrival volumes | Agmarknet | `ArrivalObservation[]` |
| Market basket definition | CommodityRegistry | Active version mappings |
| Quality flags | DataQualitySnapshot | `agmarknet_lag_hours`, coverage gaps |
| Basis fallback | Futures Agent (when licensed) | FD-030 — futures-implied spot only when Agmarknet gap |

### 3.2 Normalization

| Component | Formula (conceptual) | Lifecycle gate |
|-----------|---------------------|----------------|
| Price trend \(z_p\) | Z-score or pct change vs 30d rolling modal (primary market basket) | All stages (weight varies) |
| Arrival trend \(z_a\) | Z-score vs seasonal norm | **Oct–Mar only** (FG-01) |
| Regional strength | Cross-market dispersion index → [0, 1] | Harvest–Clearance |

Store in `signal_components`:

```json
{
  "price_trend_zscore": 0.42,
  "arrival_zscore": 1.15,
  "regional_strength_index": 0.38,
  "primary_markets_reporting_pct": 0.92
}
```

### 3.3 Direction

| Condition | Direction | Rationale |
|-----------|-----------|-----------|
| Rising modal + rising arrivals | **bearish** | Supply pressure |
| Rising modal + falling arrivals | **bullish** | Tight supply |
| Falling modal + rising arrivals | **bearish** | Harvest glut |
| Flat / conflicting | **neutral** | Low conviction |

Composite rule: weighted vote of component directions; tie → neutral.

### 3.4 Magnitude

\[
m = \mathrm{clip}_{[0,1]}\left( w_p \cdot |z_p| + w_a \cdot |z_a| \cdot g_{arrival} + w_r \cdot |I_{regional}| \right)
\]

| Symbol | Meaning |
|--------|---------|
| \(w_p, w_a, w_r\) | Registry defaults (E-02); sum ≤ 1 |
| \(g_{arrival}\) | 0 outside arrival season; 1 during Oct–Mar peak |
| \(\mathrm{clip}_{[0,1]}\) | Hard cap per TDS-004 |

### 3.5 Confidence

\[
c = c_{base} \cdot f_{coverage} \cdot (1 - \lambda_{lag}) \cdot (1 - penalty_{basis\_fallback})
\]

| Factor | Source |
|--------|--------|
| \(f_{coverage}\) | Fraction of primary markets reporting |
| \(\lambda_{lag}\) | From `agmarknet_lag_hours` / DataQualitySnapshot |
| \(penalty_{basis\_fallback}\) | Applied when using futures-implied price instead of mandi (FD-030) |

**Failure handling (TDS-004 §4.1):** Agmarknet gap → degrade confidence; do not abort if Futures + minimum agents met elsewhere.

### 3.6 Value

\[
value = \text{sign}(dir) \cdot m
\]

(Normalized signed strength; used in traceability and MI factor ranking.)

---

## 4. Weather Signal (AgentType = Weather)

**Purpose:** Rainfall, drought, production risk — including **acreage** in Phase 1 (founder clarification, TDS-004 §4.2, REQ-051).

**Optional agent:** Cotton registry marks Weather optional; absence → confidence penalty, not pipeline abort (TDS-009 §4.1).

### 4.1 Inputs

| Input | Source | Notes |
|-------|--------|-------|
| District/state rainfall | IMD API (primary) | Daily observations |
| Gap-fill / backfill | NASA POWER (secondary) | Historical bootstrap |
| Short forecast rain | IMD nowcast | Agent input only — **not** persisted as StructuredSignal until agent runs |
| Acreage proxy | State ag stats / USDA | In `signal_components` only |

### 4.2 Normalization

| Component | Normalization | Range |
|-----------|---------------|-------|
| `rainfall_anomaly_7d`, `_30d` | Departure from climatological normal | [-1, 1] scaled |
| `drought_index` | Severity composite | [0, 1] |
| `harvest_window_score` | Favorability of dry pick window | [0, 1] |
| `storage_humidity_risk` | Post-harvest humidity exposure | [0, 1] |
| `acreage_proxy_pct_change` | YoY or vs plan | [-1, 1] |
| `forecast_rain_3d_mm` | Raw mm (component only) | — |
| `primary_driver` | Enum string for traceability | — |

Example `signal_components` (WEATHER_SIGNAL_FRAMEWORK §4):

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

### 4.3 Direction

| Driver (lifecycle stage) | Typical direction |
|--------------------------|-------------------|
| Excess rain at harvest (Aug–Sep quality, Oct–Nov pick) | **bearish** (quality/supply timing) |
| Drought in growth (Aug–Sep) | **bullish** (supply fear) |
| Favorable dry harvest window | **bearish** near-term (supply flow) |
| High storage humidity risk | **bearish** (quality loss) |
| Lower acreage proxy | **bullish** (supply) |

Direction follows `primary_driver` component when \|component\| > threshold; else neutral.

### 4.4 Magnitude

\[
m = \mathrm{clip}_{[0,1]}\left( \max_i \left( |component_i| \cdot stage\_weight_i \right) \right)
\]

`stage_weight_i` from [COTTON_LIFECYCLE_SIGNAL_MAPPING.md](./COTTON_LIFECYCLE_SIGNAL_MAPPING.md) §5.2 (H=1.0, M=0.6, L=0.3).

### 4.5 Confidence

\[
c = \bar{c}_{stations} \cdot (1 - penalty_{forecast\_horizon}) \cdot (1 - penalty_{missing\_acreage})
\]

| Penalty | Trigger |
|---------|---------|
| `penalty_forecast_horizon` | IMD nowcast > 3d cap (WQ-03 open) |
| `penalty_missing_acreage` | Acreage sub-component omitted |

Missing acreage: omit sub-component, reduce confidence — **do not block** pipeline if rainfall signal valid (TDS-004 §4.2).

### 4.6 Value

\[
value = \text{sign}(dir) \cdot m
\]

---

## 5. Policy Signal (AgentType = Policy)

**Purpose:** MSP level, CCI procurement status, export restrictions (TDS-004 §4.3, REQ-052, REQ-046, FD-008).

**Decision coupling:** Policy signal exposes `cci_active_procurement` for Decision MSP/CCI floor rule; ±3% proximity computed in Decision layer from spot + registry MSP (TDS-008 §5.1).

### 5.1 Inputs

| Input | Source |
|-------|--------|
| MSP (INR/quintal) | Registry `decision_rules` + PIB announcements |
| Spot modal price | Agmarknet (derived `spot_vs_msp_pct`) |
| CCI procurement | PIB / CCI notices |
| Export restrictions | Agriculture Ministry circulars |

### 5.2 Normalization

| Component | Normalization |
|-----------|---------------|
| `msp_inr_quintal` | Absolute (from registry or PIB update) |
| `spot_vs_msp_pct` | \((P_{spot} - P_{msp}) / P_{msp}\) |
| `procurement_volume_mt_mtd` | vs seasonal norm or last year → [0, 1] scale |
| `cci_active_procurement` | boolean |
| `announcement_date` | ISO date (component metadata) |
| `geography[]` | State list when known |

Example (PROCUREMENT_SIGNAL_MODEL §3):

```json
{
  "msp_inr_quintal": 7121,
  "spot_vs_msp_pct": -0.025,
  "cci_active_procurement": true,
  "procurement_volume_mt_mtd": 125000,
  "announcement_date": "2026-06-01",
  "geography": ["Maharashtra", "Gujarat"]
}
```

### 5.3 Direction

| Condition | Direction |
|-----------|-----------|
| Spot below MSP − 3% with active CCI | **bullish** (floor support) |
| MSP hike announced | **bullish** step-change |
| Active procurement + spot near MSP | **bullish** |
| Spot well above MSP, no procurement | **neutral** to **bearish** |
| Export restriction lifted | **bullish** demand |

### 5.4 Magnitude

\[
m = \mathrm{clip}_{[0,1]}\left( \frac{|\text{spot\_vs\_msp\_pct}|}{\tau_{msp}} + \mathbb{1}_{cci} \cdot \delta_{cci} + \delta_{announcement} \right)
\]

| Parameter | Value (from baseline) |
|-----------|----------------------|
| \(\tau_{msp}\) | 0.03 (founder MSP proximity, TDS-008 §5.1) |
| \(\delta_{cci}\) | Registry PROPOSED boost when `cci_active_procurement=true` |
| \(\delta_{announcement}\) | Step boost on PIB MSP/CCI event within 7d |

### 5.5 Confidence

| Source tier | Confidence range |
|-------------|------------------|
| PIB-sourced MSP/CCI event | 0.85–0.95 |
| Registry MSP + derived spot only | 0.60–0.75 |
| Inferred from price floor alone | 0.40–0.55 |

Procurement volume is low-frequency — hold last known; decay confidence with staleness days (PROCUREMENT_SIGNAL_MODEL §6).

**Failure handling:** Stale policy data → hold last known with confidence decay (TDS-004 §4.3).

### 5.6 Value

\[
value = \text{sign}(dir) \cdot m
\]

---

## 6. Cross-Agent Notes (Downstream — Not Agent Math)

### 6.1 MI aggregation (TDS-009)

Registry `signal_weights` \(w_i\) (cotton PROPOSED):

| Agent | Weight | Required |
|-------|--------|----------|
| Futures | 0.25 | Yes |
| Market | 0.22 | Yes |
| Policy | 0.15 | No |
| Demand | 0.15 | No |
| Weather | 0.13 | No |
| Global | 0.10 | No |

\[
B = 100 \cdot \sum_{i \in \mathcal{A}^+} w_i' \cdot \max(0, s_i), \quad
R = 100 \cdot \sum_{i \in \mathcal{A}^-} w_i' \cdot \max(0, -s_i)
\]

\[
N = 100 \cdot \left(1 - \frac{|B - R|}{\max(B, R, \epsilon)}\right) \cdot \bar{c}_{agents}
\]

Regime modifiers: \(w_i' = w_i \cdot m_i(regime)\) (TDS-009 §4.3).

### 6.2 Three confidence objects (do not conflate)

| Object | Stored on | Measures |
|--------|-----------|----------|
| Agent `confidence` | `structured_signal` | Data quality for that agent |
| `forecast_confidence_h` | `ForecastVersion` horizon JSON | Price outlook reliability |
| `recommendation_confidence` | `RecommendationVersion` | Sell/hold action reliability |

Dual confidence model per TDS-009 §7 (architecture review — founder ack pending).

---

## 7. Traceability

| Spec section | TDS / REQ / FD |
|--------------|----------------|
| §2 Common contract | TDS-004 §3, REQ-060, REQ-061, FD-013 |
| §3 Market | TDS-004 §4.1, REQ-050, FD-030 |
| §4 Weather | TDS-004 §4.2, REQ-051, founder acreage clarification |
| §5 Policy | TDS-004 §4.3, TDS-008 §5.1, REQ-052, REQ-046, FD-008 |
| §6 MI aggregation | TDS-009 §3–§4 — implemented in E-05 |
| Lifecycle gates | COTTON_LIFECYCLE_SIGNAL_MAPPING §6 |

---

*End of signal math specification.*
