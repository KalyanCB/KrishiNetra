# Founder Decisions

**Source of truth:** `KrishiNetra_Founder_Thesis_Product_Spec_v5.docx` (v5.0)  
**Purpose:** Explicit founder decisions extracted for review before architecture work.

---

## Strategic Decisions (§2)

| Decision ID | Decision Description | Reasoning | Expected Impact | Related Sections |
|-------------|---------------------|-----------|-----------------|------------------|
| FD-001 | **Cotton-first validation** | Cotton is storable, high value, actively traded, futures-linked, and widely cultivated. | Reduces complexity; enables validation on a commodity with futures market and strong liquidity characteristics. Cotton becomes the reference implementation in the Commodity Registry. | §2, §5, §11, §12, §20 Phase 1 |
| FD-002 | **Net realized value** | Recommendations must account for carry costs and liquidity realities, not gross price movement alone. | Aligns product output with farmer and trader economics; evaluation and UX show outcomes as net value after carry. | §2, §4, §8, §17 |
| FD-003 | **Futures-curve benchmark** | The system must outperform futures-implied decisions before claiming value. Hold-to-futures-curve is the explicit benchmark. | Sets the bar for economic usefulness; forecast philosophy and promotion of recommendations depend on beating this benchmark net of carry. | §2, §13, §17 |
| FD-004 | **Agentic AI** | Specialized agents provide transparency and extensibility by separating concerns by signal domain. | Enables commodity-configurable extension; supports explainability and modular intelligence. | §2, §9 |
| FD-005 | **Farmers remain free** | Monetization comes later through traders, enterprise intelligence, financing, and ecosystem services—not from farmers. | Phase 1 adoption model; farmers are a long-term participant but not a near-term revenue source. | §2, §5, §19 |
| FD-006 | **Agents orchestrate; numbers decide** | Forecasting and sell/hold logic are deterministic and backtestable; agents handle orchestration and explanation, never the prediction or the recommendation math. | Makes §17 backtest and §14 calibration meaningful; load-bearing boundary for validation and trust. | §2, §9, §13, §14, §17, Changes in v5 |

---

## v5 Architectural & Product Boundary Decisions

| Decision ID | Decision Description | Reasoning | Expected Impact | Related Sections |
|-------------|---------------------|-----------|-----------------|------------------|
| FD-007 | **Deterministic vs LLM agent classification** | v5 rewrites agentic architecture: agents are classified as deterministic services vs LLM components. Forecast and sell/hold math sit in a deterministic core; agents orchestrate and explain. | Survives backtesting and calibration; prevents non-reproducible decision paths. | Changes in v5, §9, §16 |
| FD-008 | **MSP/CCI floor rule as named decision rule** | When spot is at or near the MSP floor and CCI is actively procuring, downside is partly capped and the hold calculus changes shape. Handled as an explicit rule in the deterministic Decision layer, not buried in the model. | Restores explicit policy-floor behavior in v5; auditable rule separate from forecast model. | Changes in v5, §8, §12 |
| FD-009 | **No abstract minimum useful accuracy** | The bar is the §17 backtest: does following the call beat both sell-at-harvest and hold-to-curve, net of carry? Decision value added is primary; accuracy is secondary. | Resolves prior open question on minimum accuracy; shifts evaluation from abstract accuracy thresholds to economic outcomes. | Changes in v5, §13, §22 (resolved) |
| FD-010 | **Next-commodity selection by structure, not affinity** | Storable + liquid futures + price-floor mechanism. Maize, soybean, or turmeric (NCDEX) fit; mirchi is explicitly rejected as tempting-but-wrong (no liquid futures, perishable-ish, quality-driven). | Phase 7 expansion criteria are structural; avoids hardest problem variant first. | §20 Phase 7, §22 (resolved) |

---

## Market Intelligence & Access Decisions

| Decision ID | Decision Description | Reasoning | Expected Impact | Related Sections |
|-------------|---------------------|-----------|-----------------|------------------|
| FD-011 | **Market Intelligence Mode without registration** | No registration required. Provides current prices, outlook, forecasts, confidence, bullish/bearish factors, and supply/demand analysis. | Validates the intelligence engine independently of user adoption; lowers friction for engine proof. | §7 |
| FD-012 | **Central precompute for Market Intelligence** | Domain agents and forecast run once per data refresh to produce shared Market Intelligence outlook; computed centrally and shared across all users (costs nothing per user). | Keeps eight-agent design affordable for a free product; separates shared intelligence from per-user Decision mode. | §7, §9, §16 |

---

## Agentic & Signal Decisions (§9)

| Decision ID | Decision Description | Reasoning | Expected Impact | Related Sections |
|-------------|---------------------|-----------|-----------------|------------------|
| FD-013 | **Structured signal contract** | Every domain agent emits a structured signal—value, direction, magnitude, confidence, as-of timestamp—never free text. Decision layer consumes structured data; only Explainability Agent turns structure into sentences. | Keeps Decision layer auditable; clear boundary between deterministic consumption and LLM explanation. | §9 |
| FD-014 | **Deterministic decision path** | Forecast and sell/hold math are pure functions of data-as-of-date. No LLM in prediction or decision path. | Enables exact reconstruction of past recommendations for backtest and calibration. | §9, §17 |
| FD-015 | **Per-user Decision mode scope** | Per-user Decision-mode requests run only net-of-carry math plus one explanation pass (after shared precompute). | Cost control for free farmer tier; limits compute per session while preserving personalized context. | §9, §8 |

---

## Decision Mode Output Decisions (§8)

| Decision ID | Decision Description | Reasoning | Expected Impact | Related Sections |
|-------------|---------------------|-----------|-----------------|------------------|
| FD-016 | **Sell / Hold / Partial Sell / Partial Hold outputs** | User enters commodity, quantity, storage access, liquidity need, financing profile, risk profile. Output is always one of these actions. | Standardized decision vocabulary; supports partial actions for liquidity-constrained users. | §8 |
| FD-017 | **Always net value after carry with reasoning** | Recommendations shown as net value after carry, always with reasoning. | Transparency and alignment with §2 net realized value principle. | §8, §14 |
| FD-018 | **Deterministic recommendation formula + rules** | Recommendation is net-of-carry math plus named rules, not LLM judgment. Net hold value formula includes forecast price, current price, storage, financing, quality loss, risk adjustment. | Reproducible, rule-based decision layer separate from forecast model and LLM. | §8 |

---

## Forecasting & Validation Decisions

| Decision ID | Decision Description | Reasoning | Expected Impact | Related Sections |
|-------------|---------------------|-----------|-----------------|------------------|
| FD-019 | **Economically useful recommendations over maximum accuracy** | Objective is not maximum forecast accuracy; evaluation uses directional accuracy, calibration, stability, and decision value added. | Product success tied to economic outcomes vs curve and sell-at-harvest, not headline accuracy. | §13 |
| FD-020 | **Three-strategy backtest for promotion** | Compare (1) sell immediately, (2) hold to futures curve, (3) KrishiNetra recommendation on net value added after carry. Promote recommendations only if KrishiNetra consistently adds value. | Gate for claiming product value; requires deterministic path. | §17 |
| FD-021 | **Trust via calibration, stability, data quality, transparency, outcome tracking** | Every recommendation explains: Why? What could go wrong? Which assumptions matter? | Defines trust framework components for product behavior. | §14 |

---

## Data & Roadmap Decisions

| Decision ID | Decision Description | Reasoning | Expected Impact | Related Sections |
|-------------|---------------------|-----------|-----------------|------------------|
| FD-022 | **Commodity-configurable architecture** | Commodity Registry defines per-commodity sources and drivers; architecture must remain commodity-configurable. Cotton is reference implementation. | Enables Phase 7 multi-commodity without redesigning core patterns. | §11, §16 |
| FD-023 | **Proprietary flywheel from Phase 1** | User context → recommendation → outcome captured → calibration improves → trust → usage. Proprietary dataset begins in Phase 1. | Early accumulation of decision sessions and outcomes. | §18, §20 Phase 1 |
| FD-024 | **Phased roadmap through marketplace** | Phase 1 cotton intelligence + decision engine; then personalization, inventory, behavioral learning, warehouse, financing, marketplace, additional commodities. | Sequences capability and monetization surfaces. | §20 |
| FD-025 | **Trader monetization later** | Traders: initially free; later subscription for advanced intelligence. | Revenue after value proof; farmers stay free. | §19 |
| FD-026 | **Future monetization surfaces** | Enterprise intelligence, warehouse partnerships, financing partnerships, marketplace services. | Long-term business model beyond Phase 1. | §19 |

---

## Risk Mitigation Decisions (Explicit in §21)

| Decision ID | Decision Description | Reasoning | Expected Impact | Related Sections |
|-------------|---------------------|-----------|-----------------|------------------|
| FD-027 | **Curve as explicit bar before building UX** | Mitigate forecast failing to beat curve by making the curve the explicit bar before building UX. | Prioritizes validation over surface area. | §21 |
| FD-028 | **Net-of-carry framing and partial-sell defaults** | Mitigate liquidity dominating behavior when correct holds are unactionable. | UX defaults aligned with cash-constrained farmers. | §21, §8 |
| FD-029 | **Conservative defaults for trust** | Mitigate trust loss after bad calls via calibration, stability, conservative defaults. | Reduces ruinous wrong-hold adoption risk. | §21, §14 |
| FD-030 | **Basis modeling and futures feed for data gaps** | Mitigate Agmarknet lag and gaps via basis modeling and futures feed. | Data strategy compensates for public source limitations. | §21, §10 |
| FD-031 | **Legal review for regulatory risk** | Sell/hold guidance must not drift into registrable investment advice; financing touches NBFC/RBI. | Explicit need for legal review—not a product deferral decision. | §21 |

---

## Contradictions & Ambiguities Flagged

| Item | Notes |
|------|-------|
| §16 Technical Architecture | The spec lists architecture layers (Data Ingestion → APIs → Dashboards). This is **descriptive in the founder doc**, not a decision to implement as stated; future architecture work must align to FD-006, FD-007, FD-013–FD-014 without treating §16 as an implementation mandate. |
| Update frequency | §22 states a **working answer** (daily cadence, stability-gated flips) but marks it as needing field testing—treat as provisional, not fully closed. |

---

## Decision Index (Quick Reference)

| ID | Short label |
|----|-------------|
| FD-001 | Cotton-first |
| FD-002 | Net realized value |
| FD-003 | Futures-curve benchmark |
| FD-004 | Agentic AI |
| FD-005 | Farmers free |
| FD-006 | Numbers decide |
| FD-007 | Deterministic/LLM split |
| FD-008 | MSP/CCI floor rule |
| FD-009 | DVA over min accuracy |
| FD-010 | Next commodity by structure |
| FD-011 | MI without registration |
| FD-012 | Central precompute |
| FD-013 | Structured signals |
| FD-014 | Deterministic path |
| FD-015 | Per-user decision scope |
| FD-016 | Four recommendation types |
| FD-017 | Net + reasoning always |
| FD-018 | Formula + named rules |
| FD-019 | Economic usefulness |
| FD-020 | Three-strategy backtest |
| FD-021 | Trust framework |
| FD-022 | Commodity-configurable |
| FD-023 | Flywheel Phase 1 |
| FD-024 | Phased roadmap |
| FD-025 | Trader monetization later |
| FD-026 | Future monetization |
| FD-027–FD-031 | Risk mitigations |
