# Signal Engine V1 — Domain Agent Specification

**Date:** 2026-06-04  
**PI:** PI4 Track B (KDO — docs only)  
**Epic:** E-04 — Domain Agents (Deterministic)  
**Status:** Implementation specification — **no code, no new requirements**  
**Sources:** [SIGNAL_MATH_SPECIFICATION.md](./SIGNAL_MATH_SPECIFICATION.md), TDS-004 §3–§4, TDS-009 §3–§4, TDS-007 §5.2, TDS-005 event payloads, [WEATHER_SIGNAL_FRAMEWORK.md](./WEATHER_SIGNAL_FRAMEWORK.md), [PROCUREMENT_SIGNAL_MODEL.md](./PROCUREMENT_SIGNAL_MODEL.md), [COTTON_LIFECYCLE_SIGNAL_MAPPING.md](./COTTON_LIFECYCLE_SIGNAL_MAPPING.md), [FUTURES_DEPENDENCY_ANALYSIS.md](./FUTURES_DEPENDENCY_ANALYSIS.md)

---

## 1. Purpose and E-04 Scope

This document is the **E-04 implementation contract** for five deterministic domain agents that emit one `StructuredSignal` each per daily data refresh:

| Agent | E-04 feature | Registry role (cotton PROPOSED) |
|-------|--------------|-----------------------------------|
| Market | F-04-01 | Required (`w=0.22`) |
| Weather | F-04-02 | Optional (`w=0.13`) |
| Policy | F-04-03 | Optional (`w=0.15`) |
| Futures | F-04-05 | Required (`w=0.25`) |
| Global | F-04-06 | Optional (`w=0.10`) |

**Demand Agent (F-04-04)** is out of scope here; see TDS-004 §4.4 only.

**In scope (E-04):** Per-agent inputs → feature transforms → direction → magnitude → confidence → `StructuredSignal` persistence and `SignalSnapshot` assembly (LangGraph parallel fork per TDS-004 §7.1).

**Out of scope (downstream epics):** MI aggregation B/R/N (E-05, TDS-009), forecast horizons (E-06, TDS-007), Decision NHV (E-07, TDS-008).

**Prohibited in signal payload:** free text, natural language, LLM output (TDS-004 §3, TC-003, TC-004).

---

## 2. Common StructuredSignal Contract

Per TDS-004 §3 (FD-013, REQ-060, REQ-061):

| Field | Type | Range | Rule |
|-------|------|-------|------|
| `agent_type` | enum | Market, Weather, Policy, Futures, Global | Required |
| `commodity_id` | id | `cotton` Phase 1 | Required |
| `value` | decimal | Signed normalized strength | `sign(direction) × magnitude` |
| `direction` | enum | `bullish`, `bearish`, `neutral` | vs baseline / prior regime |
| `magnitude` | decimal | **[0, 1]** | Relative strength (TDS-004 §3) |
| `confidence` | decimal | **[0, 1]** | Data completeness × freshness × horizon/source penalties |
| `as_of_timestamp` | datetime | — | Data anchor for replay (NFR-TRC-001) |
| `signal_components` | struct | — | Feature transforms; traceability only |
| `source_refs[]` | id[] | — | Observation lineage |

**Persistence validation (E-01-S05):** `magnitude`, `confidence` ∈ [0, 1] enforced at repository layer.

**Signed contribution for MI (E-05, TDS-009 §4.2):**

\[
s_i = \text{sign}(dir_i) \cdot mag_i \cdot conf_i
\]

where \(dir_i \in \{+1, 0, -1\}\) from bullish/bearish/neutral.

**Execution:** Once per **data refresh cycle** (daily, REQ-140) as part of MI precompute; idempotent by `as_of_date` (TDS-004 §8).

---

## 3. Market Signal (`agent_type = Market`)

**Purpose:** Encode domestic/regional cotton conditions — prices, arrivals, regional strength (TDS-004 §4.1, REQ-050, FD-030).

### 3.1 Inputs

| Input | Source | Observation type |
|-------|--------|------------------|
| Modal/min/max prices | Agmarknet | `PriceObservation[]` |
| Arrival volumes | Agmarknet | `ArrivalObservation[]` |
| Market basket definition | CommodityRegistry (active version) | Active mappings |
| Quality flags | DataQualitySnapshot | `agmarknet_lag_hours`, coverage gaps |
| Basis fallback | Futures Agent (when licensed) | FD-030 — futures-implied spot only when Agmarknet gap |

### 3.2 Feature Transforms

| Component | Transform | Lifecycle gate |
|-----------|-----------|----------------|
| `price_trend_zscore` (\(z_p\)) | Z-score or pct change vs 30d rolling modal (primary market basket) | All stages (weight varies) |
| `arrival_zscore` (\(z_a\)) | Z-score vs seasonal norm | **Oct–Mar only** (FG-01) |
| `regional_strength_index` (\(I_{regional}\)) | Cross-market dispersion index → [0, 1] | Harvest–Clearance |
| `primary_markets_reporting_pct` | Fraction of primary basket markets reporting | Coverage factor input |

Example `signal_components`:

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
| \(f_{coverage}\) | `primary_markets_reporting_pct` |
| \(\lambda_{lag}\) | From `agmarknet_lag_hours` / DataQualitySnapshot |
| \(penalty_{basis\_fallback}\) | Applied when using futures-implied price instead of mandi (FD-030) |

**Failure handling (TDS-004 §4.1):** Agmarknet gap → degrade confidence; emit signal with penalty in `source_refs`; do not abort MI if Futures + minimum agents met elsewhere.

### 3.6 Value

\[
value = \text{sign}(dir) \cdot m
\]

---

## 4. Weather Signal (`agent_type = Weather`)

**Purpose:** Rainfall, drought, production risk — including **acreage** in Phase 1 (founder clarification, TDS-004 §4.2, REQ-051).

**Optional agent:** Cotton registry marks Weather optional; absence → confidence penalty at MI layer, not pipeline abort (TDS-009 §4.1).

### 4.1 Inputs

| Input | Source | Notes |
|-------|--------|-------|
| District/state rainfall | IMD API (primary) | Daily observations |
| Gap-fill / backfill | NASA POWER (secondary) | Historical bootstrap |
| Short forecast rain | IMD nowcast | Agent input only — **not** persisted as StructuredSignal until agent runs |
| Acreage proxy | State ag stats / USDA | In `signal_components` only |
| Historical norms | Registry `weather_variables` | Climatological baselines |

### 4.2 Feature Transforms

| Component | Transform | Range |
|-----------|-----------|-------|
| `rainfall_anomaly_7d`, `_30d` | Departure from climatological normal | [-1, 1] scaled |
| `drought_index` | Severity composite | [0, 1] |
| `harvest_window_score` | Favorability of dry pick window | [0, 1] |
| `storage_humidity_risk` | Post-harvest humidity exposure | [0, 1] |
| `acreage_proxy_pct_change` | YoY or vs plan | [-1, 1] |
| `forecast_rain_3d_mm` | Raw mm (component only) | — |
| `primary_driver` | Enum string for traceability | — |

Example `signal_components`:

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

## 5. Policy Signal (`agent_type = Policy`)

**Purpose:** MSP level, CCI procurement status, export restrictions (TDS-004 §4.3, REQ-052, REQ-046, FD-008).

**Decision coupling:** Policy signal exposes `cci_active_procurement` for Decision MSP/CCI floor rule; ±3% proximity computed in Decision layer from spot + registry MSP (TDS-008 §5.1). Enables `MSP_FLOOR` regime detection (TDS-009 §5.1).

### 5.1 Inputs

| Input | Source |
|-------|--------|
| MSP (INR/quintal) | Registry `decision_rules` + PIB announcements |
| Spot modal price | Agmarknet (derived `spot_vs_msp_pct`) |
| CCI procurement | PIB / CCI notices |
| Export restrictions | Agriculture Ministry circulars |

### 5.2 Feature Transforms

| Component | Transform |
|-----------|-----------|
| `msp_inr_quintal` | Absolute (from registry or PIB update) |
| `spot_vs_msp_pct` | \((P_{spot} - P_{msp}) / P_{msp}\) |
| `procurement_volume_mt_mtd` | vs seasonal norm or last year → [0, 1] scale |
| `cci_active_procurement` | boolean |
| `export_restriction_flag` | 0/1 from circular status |
| `announcement_date` | ISO date (component metadata) |
| `geography[]` | State list when known |

Example `signal_components`:

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
| Export restriction imposed | **bearish** export channel |

### 5.4 Magnitude

\[
m = \mathrm{clip}_{[0,1]}\left( \frac{|\text{spot\_vs\_msp\_pct}|}{\tau_{msp}} + \mathbb{1}_{cci} \cdot \delta_{cci} + \delta_{announcement} + \delta_{export} \right)
\]

| Parameter | Value (from baseline) |
|-----------|----------------------|
| \(\tau_{msp}\) | 0.03 (founder MSP proximity, TDS-008 §5.1) |
| \(\delta_{cci}\) | Registry PROPOSED boost when `cci_active_procurement=true` |
| \(\delta_{announcement}\) | Step boost on PIB MSP/CCI event within 7d |
| \(\delta_{export}\) | Registry PROPOSED step on export policy change within 7d |

### 5.5 Confidence

| Source tier | Confidence range |
|-------------|------------------|
| PIB-sourced MSP/CCI event | 0.85–0.95 |
| Registry MSP + derived spot only | 0.60–0.75 |
| Inferred from price floor alone | 0.40–0.55 |

Procurement volume is low-frequency — hold last known; decay confidence with staleness days ([PROCUREMENT_SIGNAL_MODEL.md](./PROCUREMENT_SIGNAL_MODEL.md) §6).

**Failure handling:** Stale policy data → hold last known with confidence decay (TDS-004 §4.3).

### 5.6 Value

\[
value = \text{sign}(dir) \cdot m
\]

---

## 6. Futures Signal (`agent_type = Futures`)

**Purpose:** Futures curve, basis, open interest — benchmark signal for hold-to-curve (FD-003, REQ-082) and basis modeling (FD-030, REQ-133). **Required** for cotton MI publish (TDS-009 §4.1, §9).

### 6.1 Inputs

| Input | Source | Observation type |
|-------|--------|------------------|
| Near/far contract prices | Licensed commercial feed (REQ-071) | `FuturesObservation[]` |
| Open interest, volume | Same feed | OI/volume fields |
| Spot modal price | Agmarknet (or MI `current_price`) | Basis denominator |
| Curve snapshot ref | Ingestion event | TDS-005 `curve_snapshot_ref` |
| Feed health | DataQualitySnapshot | `futures_feed_ok` (E-01-S08) |
| Registry mappings | CommodityRegistry | Contract months, scaling |

### 6.2 Feature Transforms

Aligned to TDS-007 §5.2 futures features (stored in `signal_components`):

| Component | Transform | Range / notes |
|-----------|-----------|---------------|
| `curve_slope` | Normalized \((P_{near} - P_{far}) / P_{near}\) or registry-defined slope | Signed; backwardation → positive |
| `curve_level_near` | Near-month price level vs 30d rolling mean → z-score | [-1, 1] scaled |
| `open_interest_change` | Δ OI vs prior session / 20d mean → z-score | [-1, 1] scaled |
| `basis_futures_spot` | \((P_{futures,near} - P_{spot}) / P_{spot}\) | Signed pct |
| `carry_implied_30` | Implied carry from curve to 30d horizon | Registry formula |
| `carry_implied_60`, `_90` | Same at 60/90d | Optional components |
| `primary_driver` | Enum: `curve_slope`, `basis`, `open_interest`, `carry` | Traceability |

Example `signal_components`:

```json
{
  "curve_slope": 0.018,
  "curve_level_near_zscore": 0.55,
  "open_interest_change_zscore": -0.31,
  "basis_futures_spot": -0.012,
  "carry_implied_30": 0.009,
  "carry_implied_60": 0.017,
  "primary_driver": "curve_slope"
}
```

### 6.3 Direction

| Condition | Direction | Rationale |
|-----------|-----------|-----------|
| Steep backwardation (`curve_slope` > threshold) | **bullish** | Hold-to-curve incentive (FD-003); feeds `CURVE_BACKWARDATION` regime |
| Contango (`curve_slope` < −threshold) | **bearish** | Carry cost / sell bias |
| Rising OI + rising near price | **bullish** | New long positioning |
| Rising OI + falling near price | **bearish** | New short pressure |
| Basis widening (futures premium vs spot) | **bullish** | Tight physical vs paper |
| Basis narrowing / negative extreme | **bearish** | Weak paper premium |

Composite rule: direction follows `primary_driver` when \|component\| > registry threshold; weighted vote on curve + basis for tie-break; else **neutral**.

### 6.4 Magnitude

\[
m = \mathrm{clip}_{[0,1]}\left( w_s \cdot |z_{slope}| + w_b \cdot |z_{basis}| + w_o \cdot |z_{oi}| + w_c \cdot |carry\_implied_{h^*}| \right)
\]

| Symbol | Meaning |
|--------|---------|
| \(w_s, w_b, w_o, w_c\) | Registry defaults (E-02); sum ≤ 1 |
| \(z_{slope}, z_{basis}, z_{oi}\) | Z-scored transforms above |
| \(h^*\) | Nearest registry horizon (30d default) |

### 6.5 Confidence

\[
c = c_{base} \cdot f_{feed} \cdot (1 - \lambda_{staleness}) \cdot (1 - penalty_{thin\_oi}) \cdot (1 - penalty_{spot\_gap})
\]

| Factor | Source |
|--------|--------|
| \(f_{feed}\) | 1.0 when `futures_feed_ok=true`; **≤ 0.35** when degraded (DS-001 interim) |
| \(\lambda_{staleness}\) | Session age vs EOD expectation |
| \(penalty_{thin\_oi}\) | OI/volume below registry floor |
| \(penalty_{spot\_gap}\) | Missing concurrent Agmarknet spot for basis |

**Failure handling (TDS-004 §4.5):** Missing licensed feed → emit **degraded** signal with explicit confidence penalty and `source_refs` noting gap; **strict** MI path blocks publish when Futures absent from `required_agents[]` (TDS-009 §9). Critical for DVA: hold-to-curve benchmark undefined without licensed curve (FD-003).

### 6.6 Value

\[
value = \text{sign}(dir) \cdot m
\]

---

## 7. Global Signal (`agent_type = Global`)

**Purpose:** International demand and global inventory conditions (TDS-004 §4.6, REQ-055). Feeds supply/demand narrative inputs and TDS-007 global features.

### 7.1 Inputs

| Input | Source | Notes |
|-------|--------|-------|
| Global ending stocks | USDA FAS / WASDE | Monthly release cycle |
| World consumption / offtake | USDA, ICAC | Monthly |
| Global demand index inputs | Registry `global_drivers` | Composite weights |
| Prior period values | Feature store / last signal | Hold-forward between releases |
| Source terms | ICAC approval status | Confidence tier |

### 7.2 Feature Transforms

Aligned to TDS-007 §5.2 global features:

| Component | Transform | Range |
|-----------|-----------|-------|
| `global_inventory_zscore` | Z-score of world ending stocks vs 5y rolling mean | [-1, 1] scaled |
| `global_inventory_level` | Absolute level (metadata) | — |
| `global_demand_index` | Weighted composite of consumption trend + export demand proxy | [0, 1] normalized |
| `global_demand_trend` | Slope of consumption series over 3 releases | [-1, 1] scaled |
| `release_staleness_days` | Days since last USDA/ICAC publish | Metadata |
| `primary_driver` | Enum: `inventory`, `demand` | Traceability |

Example `signal_components`:

```json
{
  "global_inventory_zscore": -0.48,
  "global_inventory_level_mt": 82.4,
  "global_demand_index": 0.62,
  "global_demand_trend": 0.04,
  "release_staleness_days": 12,
  "primary_driver": "inventory"
}
```

### 7.3 Direction

| Condition | Direction | Rationale |
|-----------|-----------|-----------|
| Falling global inventory z-score (tight world stocks) | **bullish** | Supply constraint |
| Rising global inventory z-score | **bearish** | Ample world supply |
| Rising global demand index / trend | **bullish** | Demand pull |
| Falling global demand index / trend | **bearish** | Demand weakness |
| Conflicting inventory vs demand | **neutral** | Offsetting forces |

Direction follows `primary_driver` when \|component\| > threshold; else weighted vote inventory vs demand.

### 7.4 Magnitude

\[
m = \mathrm{clip}_{[0,1]}\left( w_i \cdot |z_{inventory}| + w_d \cdot |z_{demand}| \right)
\]

| Symbol | Meaning |
|--------|---------|
| \(w_i, w_d\) | Registry defaults (E-02); sum ≤ 1 |
| \(z_{inventory}\) | `global_inventory_zscore` |
| \(z_{demand}\) | Normalized deviation of `global_demand_index` from 0.5 baseline |

### 7.5 Confidence

\[
c = c_{tier} \cdot (1 - penalty_{staleness}) \cdot (1 - penalty_{single\_source})
\]

| Factor | Source |
|--------|--------|
| \(c_{tier}\) | USDA primary: 0.80–0.90; ICAC-only: 0.65–0.75; hold-forward: decay from prior |
| \(penalty_{staleness}\) | `release_staleness_days` vs monthly cadence (>45d → steep decay) |
| \(penalty_{single\_source}\) | Only one of USDA/ICAC available |

**Failure handling (TDS-004 §4.6):** Use last available with confidence decay; do not block Forecast if `minimum_agents` met without Global.

### 7.6 Value

\[
value = \text{sign}(dir) \cdot m
\]

---

## 8. SignalSnapshot Assembly (E-04 Orchestration)

Per TDS-004 §7.1 LangGraph MI refresh graph:

| Step | Action |
|------|--------|
| 1 | Trigger: `DATA_REFRESH_START` after ingestion join |
| 2 | Fork: run Market, Weather, Policy, Futures, Global agents **in parallel** |
| 3 | Each agent: load registry config → observations → compute §3–§7 → persist `StructuredSignal` |
| 4 | Join: assemble `SignalSnapshot` with all agent rows + `as_of_date` |
| 5 | Validate: `required_agents[]` present (cotton: Market, Futures) before Forecast handoff |
| 6 | Pass snapshot to Forecast Agent (E-06) and MI Framework (E-05) |

**Missing optional agent:** omit row or emit null with MI-level penalty — do not abort (TDS-009 §4.1).

**Missing required agent:** no MI publish; alert ops (TDS-009 §9).

---

## 9. Downstream MI Hooks (Reference — E-05)

Not implemented in E-04; agents must emit fields consumed here:

| Construct | Use |
|-----------|-----|
| Signed \(s_i\) | B/R/N aggregation (TDS-009 §3) |
| `market_regime` inputs | `TIGHT_SUPPLY` uses Market `arrival_zscore`; `CURVE_BACKWARDATION` uses Futures `curve_slope`; `MSP_FLOOR` uses Policy `cci_active_procurement` + spot (TDS-009 §5.1) |
| `bullish_factors[]` / `bearish_factors[]` | Rank by \|s_i w_i'\| from agent `signal_components` labels (TDS-009 §6.2) |
| Three confidence objects | Agent `confidence` ≠ forecast confidence ≠ recommendation confidence (TDS-009 §7) |

Cotton PROPOSED weights (TDS-009 §4.1): Futures 0.25, Market 0.22, Policy 0.15, Weather 0.13, Global 0.10 (Demand 0.15 — not in this doc).

---

## 10. E-04 Acceptance Checklist

| ID | Criterion | Source |
|----|-----------|--------|
| AC-01 | Each agent emits valid StructuredSignal per §2 | TDS-004 §3 |
| AC-02 | Market/Weather/Policy math matches §3–§5 | SIGNAL_MATH_SPECIFICATION |
| AC-03 | Futures/Global math matches §6–§7 | TDS-004 §4.5–4.6, TDS-007 §5.2 |
| AC-04 | No LLM / free text in payloads | TC-003, TC-004 |
| AC-05 | `source_refs[]` lineage to E-03 observations | TDS-004 §10 |
| AC-06 | LangGraph parallel fork + join produces SignalSnapshot | TDS-004 §7.1 |
| AC-07 | Required-agent gate enforced before Forecast | TDS-009 §9 |
| AC-08 | Global Agent package path: `agents/global_signals/` | ADR-005 |

---

## 11. Traceability

| Spec section | TDS / REQ / FD |
|--------------|----------------|
| §2 Common contract | TDS-004 §3, REQ-060, REQ-061, FD-013 |
| §3 Market | TDS-004 §4.1, REQ-050, FD-030 |
| §4 Weather | TDS-004 §4.2, REQ-051 |
| §5 Policy | TDS-004 §4.3, TDS-008 §5.1, REQ-052, REQ-046, FD-008 |
| §6 Futures | TDS-004 §4.5, REQ-054, REQ-082, REQ-133, FD-003, FD-030 |
| §7 Global | TDS-004 §4.6, REQ-055 |
| §8 Orchestration | TDS-004 §7–§8, TDS-005 |
| §9 MI hooks | TDS-009 §3–§7 — E-05 |
| Lifecycle gates | COTTON_LIFECYCLE_SIGNAL_MAPPING §5–§6 |

---

*End of Signal Engine V1 specification.*
