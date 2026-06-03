# Assumptions

**Source of truth:** `KrishiNetra_Founder_Thesis_Product_Spec_v5.docx` (v5.0)  
**Note:** Assumptions stated or strongly implied in the founder spec. Inferred items are marked **PROPOSED ASSUMPTION**.

---

## Business Assumptions

| ID | Assumption | Evidence in spec | Classification |
|----|------------|------------------|----------------|
| BA-001 | Farmers and traders improve realized outcomes when market intelligence is combined with personal context, liquidity constraints, financing realities, and explainable reasoning. | §1 central hypothesis | Explicit |
| BA-002 | The primary product gap is contextual decision intelligence, not information availability. | §3 | Explicit |
| BA-003 | KrishiNetra can become the intelligence layer for agricultural inventory decisions across the long-term participant set (farmers, traders, ginners, processors, warehouses, lenders, exporters). | §5 | Explicit |
| BA-004 | Monetization from farmers in Phase 1 is not required; traders and future enterprise/ecosystem surfaces will fund the business later. | §2 Decision 5, §19 | Explicit |
| BA-005 | A proprietary dataset from decision sessions and outcomes creates competitive advantage unavailable from public data alone. | §18 | Explicit |
| BA-006 | Traders will eventually pay for advanced intelligence via subscription after initial free period. | §19 | Explicit |
| BA-007 | **PROPOSED ASSUMPTION:** Enterprise (procurement/inventory intelligence) persona demand exists but is deferred until after cotton farmer/trader value is proven. | §6 Future enterprise, §20 Phases 2+ | Inferred from phasing |

---

## Market Assumptions

| ID | Assumption | Evidence in spec | Classification |
|----|------------|------------------|----------------|
| MA-001 | Farmers frequently sell at harvest due to liquidity requirements rather than market expectations. | §3 | Explicit |
| MA-002 | Traders often hold inventory without a rigorous risk-adjusted framework. | §3 | Explicit |
| MA-003 | Current systems provide prices and news but not decision support. | §3 | Explicit |
| MA-004 | Cotton market characteristics (storable, futures-linked, active trade) make it a viable first validation market. | §2, §12 | Explicit |
| MA-005 | Maize, soybean, or turmeric (NCDEX) are structurally suitable follow-on commodities; mirchi is structurally unsuitable for early expansion. | §20 Phase 7 | Explicit |
| MA-006 | **PROPOSED ASSUMPTION:** Market Intelligence Mode without registration is sufficient to validate the intelligence engine before broad user adoption. | §7 | Explicit intent |
| MA-007 | **PROPOSED ASSUMPTION:** Local trust can be destroyed by a single highly visible wrong hold recommendation. | §21 trust loss risk | Explicit risk implies assumption |

---

## Data Assumptions

| ID | Assumption | Evidence in spec | Classification |
|----|------------|------------------|----------------|
| DA-001 | Public sources (Agmarknet, eNAM, IMD, Agriculture Ministry, USDA, ICAC) are usable for cotton intelligence. | §10 | Explicit |
| DA-002 | Commercial futures feeds and industry reports are obtainable and materially improve intelligence. | §10 | Explicit |
| DA-003 | Agmarknet lag and gaps cap achievable accuracy; futures feed and basis modeling partially compensate. | §21 | Explicit |
| DA-004 | Cotton signals listed (arrivals, futures curve, MSP, CCI procurement, mill demand, exports, weather, acreage, global inventories) are sufficient for 30/60/90-day outlooks with confidence bands. | §12 | Explicit |
| DA-005 | Each commodity in the registry can be defined by price sources, arrival sources, demand drivers, policy drivers, weather variables, quality dimensions, storage characteristics, and forecast horizons. | §11 | Explicit |
| DA-006 | User-entered context (commodity, quantity, storage, liquidity, financing, risk profiles) is accurate enough for net-of-carry math. | §8 | **PROPOSED ASSUMPTION** (input quality not specified) |
| DA-007 | Outcomes from decision sessions can be captured and fed back into calibration. | §18, §14 outcome tracking | Explicit |
| DA-008 | **PROPOSED ASSUMPTION:** Daily data refresh cadence is adequate for cotton market intelligence in Phase 1. | §22 working answer on update frequency | Partially specified |

---

## Technical Assumptions

| ID | Assumption | Evidence in spec | Classification |
|----|------------|------------------|----------------|
| TA-001 | Deterministic forecast and decision functions can be reconstructed for any historical as-of-date given the same inputs. | §9, §17 | Explicit |
| TA-002 | Eight-agent design (six deterministic domain agents + forecast + decision + two LLM agents) is affordable when Market Intelligence is centrally precomputed. | §9, §12 central precompute | Explicit |
| TA-003 | Structured signals (value, direction, magnitude, confidence, as-of timestamp) are sufficient for the Decision layer. | §9 signal contract | Explicit |
| TA-004 | LLM Explainability and Conversation components can produce human-readable reasoning without affecting deterministic outputs. | §9 | Explicit |
| TA-005 | 30/60/90-day forecast horizons are the operative outlook windows for cotton. | §9 Forecast agent, §12 | Explicit |
| TA-006 | Architecture can remain commodity-configurable across phases without rewriting the deterministic core pattern. | §11, §16 | Explicit |
| TA-007 | **PROPOSED ASSUMPTION:** Stability constraint can gate recommendation flips so noise does not change calls daily. | §22 working answer | Partially specified |
| TA-008 | **PROPOSED ASSUMPTION:** Partial-sell defaults are implementable as product behavior without financing integration in Phase 1. | §21 mitigation | Inferred from Phase 1 scope |

---

## Assumption Summary by Type

| Category | Explicit | PROPOSED ASSUMPTION |
|----------|----------|---------------------|
| Business | 6 | 1 |
| Market | 6 | 2 |
| Data | 5 | 3 |
| Technical | 6 | 2 |

---

## Items Explicitly NOT Assumed (Spec Gaps)

The founder spec does **not** assume:

- Specific minimum directional or point forecast accuracy thresholds (explicitly rejected in v5).
- Final trust-score UI design.
- Exact financing introduction trigger.
- Completed legal classification of sell/hold guidance.
- Specific commercial data vendor contracts or costs.

These remain open questions, constraints, or external decisions—see `OPEN_QUESTIONS.md` and `CONSTRAINTS.md`.
