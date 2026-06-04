# Procurement Signal Model — Phase 1 Cotton

**Date:** 2026-06-04  
**Epic:** E-01 Phase 4 (research)  
**Status:** Research — Policy agent input design  
**Sources:** TDS-004 (Policy agent), TDS-008 (MSP/CCI rules), TDS-006 §3.8, founder MSP ±3% rule

---

## 1. Purpose

Evaluate whether **government procurement** (CCI cotton operations, MSP announcements, PIB releases) can be a **first-class StructuredSignal** (Policy agent) with sufficient source access, frequency, and reliability.

---

## 2. Procurement Concepts (Cotton)

| Concept | Description | Decision relevance |
|---------|-------------|-------------------|
| **MSP** | Minimum Support Price floor | `msp_proximity_triggered` when spot within ±3% |
| **CCI procurement** | Cotton Corporation of India buying | Floor support; `cci_active_procurement` flag (TDS-004) |
| **Announcement** | Cabinet/ ministry price fixes | Step-change in policy signal |
| **Volume** | Quantities procured by region | Supply removal from open market |
| **Geography** | State/mandi coverage | Regional price floor effects |

---

## 3. Can Procurement Be First-Class Signal?

| Criterion | Assessment |
|-----------|------------|
| **Predictive for price?** | **Yes, near-term** — active CCI buying supports floor; announcement shocks move basis |
| **Structured enough?** | **Partially** — boolean flags + volumes mappable to `signal_components` |
| **Daily granularity?** | **No** — procurement is event/volume periodic, not daily like mandi |
| **Agent fit** | **Policy agent** (`agent_type=Policy`), not Market observation |

**Verdict:** Procurement should be a **first-class Policy StructuredSignal**, not a price observation. Components:

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

---

## 4. Source Inventory

| Source | Content | Access | Frequency | Reliability |
|--------|---------|--------|-----------|-------------|
| **PIB** | MSP announcements, CCI press releases | [pib.gov.in](https://pib.gov.in) RSS/HTML | Event-driven | **High** (official) |
| **CCI website** | Procurement notices, centers | Public web | Weekly–seasonal | **Medium** (manual scrape risk) |
| **DAC&FW / Agri Ministry** | Policy circulars | PDF/web | Seasonal | **High** |
| **Agmarknet** | Indirect (price vs MSP) | OGD API | Daily | Derived, not procurement volume |
| **RTI / annual reports** | Historical procurement volumes | Manual | Annual | Backfill only |

---

## 5. Accessibility and Licensing

| Source | Licensing | Automation |
|--------|-----------|------------|
| PIB | Government open press — attribution | RSS/HTML parse; no API |
| CCI | Public notices; confirm ToS before scraper | Likely manual + structured entry Phase 1 |
| MSP values | Published annually | Seed in registry `decision_rules` + Policy signal update on change |

---

## 6. Signal Construction Rules

1. **MSP proximity:** Computed from Agmarknet modal vs registry MSP → feeds Policy components and Decision `msp_proximity_triggered`.
2. **CCI active flag:** Set true when published procurement window open in target states.
3. **Volume:** Monthly MT procured; low frequency → hold last known in signal until update (document staleness in confidence).
4. **Confidence:** High when PIB-sourced; lower when inferred from price floor alone.

---

## 7. Gaps and Blockers

| Gap | Mitigation |
|-----|------------|
| No machine-readable CCI API | Manual CSV seed + PIB watcher (E-03) |
| Volume reporting lag | Use announcement events as primary; volume as secondary |
| State-level procurement granularity | Start national + top-3 cotton states |

---

## 8. Recommendation

| Question | Answer |
|----------|--------|
| First-class signal? | **Yes** — Policy agent StructuredSignal |
| Primary source Phase 1 | PIB + registry MSP + derived spot proximity |
| Production automation | **Conditional** — event ingest feasible; volume series needs manual/RTI backfill |

---

*End of procurement signal model.*
