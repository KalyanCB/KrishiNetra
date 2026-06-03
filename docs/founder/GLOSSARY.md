# Glossary

**Source of truth:** `KrishiNetra_Founder_Thesis_Product_Spec_v5.docx` (v5.0)  
Domain terms used in KrishiNetra founder intent. Definitions preserve founder language where possible; scope is limited to the spec.

---

## Core Product Concepts

| Term | Definition | Source |
|------|------------|--------|
| **KrishiNetra** | Intelligence layer for agricultural inventory decisions; answers "What should I do next?" rather than only "What is today's price?" | §1, §5 |
| **Decision intelligence** | Market intelligence combined with personal context, liquidity constraints, financing realities, and explainable reasoning to improve realized outcomes | §1, §3 |
| **Contextual decision intelligence** | Decision support that integrates user-specific constraints with market signals—the stated gap current price/news systems do not fill | §3 |
| **Market Intelligence Mode** | Unregistered access mode providing prices, outlook, forecasts, confidence, bullish/bearish factors, and supply/demand analysis to validate the engine | §7 |
| **Decision Mode** | User-provided context mode producing Sell/Hold/Partial recommendations net of carry with reasoning | §8 |

---

## Economic & Recommendation Terms

| Term | Definition | Source |
|------|------------|--------|
| **Net realized value** | Recommendations and evaluations account for carry costs and liquidity realities, not gross price movement alone | §2, §4 |
| **Net value / net of carry** | Recommendation and backtest outcomes expressed after storage, financing, quality loss, and risk adjustments | §8, §17 |
| **Carry cost** | Costs of holding inventory including storage, financing (cost of capital), expected quality loss, and risk adjustment in the hold calculus | §8 formula |
| **Net hold value** | Approximate value of holding: forecast price(h) − current price − storage(h) − financing(h, cost of capital) − expected quality loss(h) − risk adjustment | §8 |
| **Sell at harvest** | Baseline behavior where farmers sell due to liquidity rather than market expectations; benchmark strategy (1) in backtest | §3, §17 |
| **Hold-to-futures-curve** | Benchmark strategy (2): holding implied by futures curve; system must outperform before claiming value | §3, §13, §17 |
| **Decision value added (DVA)** | Primary evaluation metric: economic value of following KrishiNetra vs benchmarks, net of carry; supersedes abstract minimum accuracy | §13 |
| **Partial Sell / Partial Hold** | Recommendation types for liquidity-constrained users who cannot fully sell or fully hold | §8, §21 |
| **Conservative defaults** | Product defaults (including partial-sell) chosen to reduce trust loss from aggressive hold calls | §21 |

---

## Market & Cotton Terms

| Term | Definition | Source |
|------|------------|--------|
| **Cotton-first** | Strategic choice to validate on cotton: storable, high value, actively traded, futures-linked, widely cultivated | §2, §12 |
| **Commodity Registry** | Per-commodity definition of price sources, arrival sources, demand drivers, policy drivers, weather variables, quality dimensions, storage characteristics, and forecast horizons; cotton is reference implementation | §11 |
| **Cotton Intelligence Model** | Signal set and outputs for cotton: arrivals, futures curve, MSP, CCI procurement, mill demand, exports, weather, acreage, global inventories → 30/60/90-day outlooks with confidence bands | §12 |
| **Futures curve** | Term structure of futures prices; used as intelligence signal and as hold benchmark | §9, §12, §17 |
| **Basis** | Relationship between spot/local prices and futures (implied by "basis modeling" mitigating Agmarknet gaps) | §21 |
| **Open interest** | Futures market participation metric emitted by Futures agent | §9 |
| **Arrivals** | Physical market arrival flow signal | §9, §12 |
| **Regional strength** | Relative strength of regional markets in Market agent output | §9 |
| **Acreage** | Planted area signal in cotton model | §12 |
| **Global inventories** | International inventory levels in Global agent / cotton model | §9, §12 |

---

## Policy & India-Specific Terms

| Term | Definition | Source |
|------|------------|--------|
| **MSP** | Minimum Support Price; policy floor affecting downside when spot is at or near floor | §8, §12 |
| **CCI** | Cotton Corporation of India; procurement activity affects hold calculus when actively procuring near MSP floor | §8, §12 |
| **MSP/CCI floor rule** | Named deterministic rule: when spot at or near MSP and CCI actively procuring, downside partly capped and hold calculus changes shape | §8 |
| **Agmarknet** | Indian public mandi price source; subject to lag and gaps | §10, §21 |
| **eNAM** | National Agriculture Market platform; public price source | §10 |
| **IMD** | India Meteorological Department; weather data source | §10 |
| **NCDEX** | Exchange referenced for turmeric as structurally suitable commodity | §20 |
| **NBFC / RBI** | Regulatory bodies relevant when financing features are introduced | §21 |

---

## Data & Organization Terms

| Term | Definition | Source |
|------|------------|--------|
| **Structured signal** | Domain agent output: value, direction, magnitude, confidence, as-of timestamp—never free text to Decision layer | §9 |
| **Signal contract** | Requirement that all domain agents emit structured signals for auditability | §9 |
| **As-of date / data-as-of-date** | Temporal anchor for reproducible forecast and decision outputs | §9, §17 |
| **Central precompute** | Domain agents and forecast run once per data refresh; shared Market Intelligence for all users | §9, §7 |
| **Data refresh** | Cadence at which domain agents and forecast rerun (working answer: daily) | §9, §22 |
| **Proprietary data flywheel** | context → recommendation → outcome → calibration → trust → usage → proprietary dataset growth | §18 |
| **Decision session** | Instance linking user context to a recommendation | §15 |
| **Outcome** | Captured realized result of a decision session for calibration | §15, §18 |
| **User context** | Commodity, quantity, storage access, liquidity need, financing profile, risk profile | §8, §15 |
| **Farmer intent / trader intent** | Proprietary behavioral signals captured in later phases | §10, §20 Phase 3 |

---

## Agent & Architecture Terms (Product-Level)

| Term | Definition | Source |
|------|------------|--------|
| **Agentic AI** | Specialized agents by signal domain for transparency and extensibility | §2, §9 |
| **Deterministic service** | Non-LLM agent implementation producing structured signals or model outputs | §9 |
| **Domain agent** | Market, Weather, Policy, Demand, Futures, or Global agent | §9 |
| **Forecast agent** | Deterministic model producing 30/60/90-day outlook with probability bands | §9 |
| **Decision agent / Decision layer** | Deterministic math + named rules producing recommendation | §9, §8 |
| **Explainability agent** | LLM converting structured signals to human-readable reasoning | §9 |
| **Conversation agent** | LLM for natural-language Q&A over explanations | §9 |
| **Deterministic core** | Forecast + decision math isolated from LLM layer | §9, §16 |
| **Feature Store** | Layer name in founder architecture stack (ingestion pipeline concept) | §16 |
| **Agent orchestration** | Coordination of agents; orchestration does not perform prediction math | §2, §16 |

---

## Forecasting, Trust & Validation Terms

| Term | Definition | Source |
|------|------------|--------|
| **30/60/90-day outlook** | Standard forecast horizons with confidence bands | §9, §12 |
| **Confidence bands** | Probability bands accompanying point/directional outlook | §12 |
| **Directional accuracy** | Forecast evaluation dimension (secondary to DVA) | §13 |
| **Calibration** | Alignment between stated confidence and realized outcomes; trust component and flywheel input | §13, §14, §18 |
| **Stability** | Resistance to noisy recommendation flips; evaluation and gating dimension | §13, §14, §22 |
| **Material signal movement** | Threshold concept (undefined) for when stability constraint allows recommendation flip | §22 |
| **Transparency** | Trust component; explicit reasoning and assumptions | §14 |
| **Outcome tracking** | Trust component; linking recommendations to results | §14 |
| **Backtest** | Historical comparison of three strategies on net value added | §17 |
| **Promotion (recommendations)** | Elevating live recommendations only after consistent net value added in backtest | §17 |
| **Bullish/bearish factors** | Market Intelligence explanatory market drivers | §7 |

---

## Participant & Business Terms

| Term | Definition | Source |
|------|------------|--------|
| **Farmer persona** | Phase 1 user seeking decision intelligence | §6 |
| **Trader persona** | Phase 1 user seeking portfolio intelligence | §6 |
| **Future enterprise** | Procurement and inventory intelligence participant (post–Phase 1) | §6 |
| **Inventory intelligence** | Long-term capability for inventory decision support | §5 |
| **Portfolio intelligence** | Trader-facing framing of intelligence | §6 |
| **Inventory registration** | Phase 2 capability; gate for financing consideration | §20, §22 |
| **Advanced intelligence** | Future paid trader subscription tier | §19 |

---

## Risk & Regulatory Terms

| Term | Definition | Source |
|------|------------|--------|
| **Registrable investment advice** | Regulatory category sell/hold guidance must avoid | §21 |
| **Liquidity constraints** | Cash/loan timing needs that override theoretically optimal holds | §3, §4, §21 |
| **Cost of capital** | Input to financing(h) in net hold value | §8 |
| **Quality loss** | Expected degradation over hold horizon h | §8 |
| **Risk adjustment** | Adjustment in net hold value formula for user risk profile | §8 |
| **Risk tolerance** | Farmer economic attribute | §4 |
| **Working-capital cost** | Trader economic attribute | §4 |

---

## Roadmap Phase Labels

| Term | Definition | Source |
|------|------------|--------|
| **Phase 1** | Cotton intelligence + decision engine | §20 |
| **Phase 2** | Personalization and inventory registration | §20 |
| **Phase 3** | Behavioral learning and intent capture | §20 |
| **Phase 4** | Warehouse integration | §20 |
| **Phase 5** | Financing | §20 |
| **Phase 6** | Marketplace | §20 |
| **Phase 7** | Additional commodities (structural selection) | §20 |

---

## Terms Referenced in Examples but Minimal Spec Detail

| Term | Notes |
|------|-------|
| **Mirchi** | Explicitly unsuitable early commodity (no liquid futures, perishable-ish, quality-driven) | §20 |
| **Maize / soybean / turmeric** | Structurally suitable follow-on commodities | §20 |
| **Ginners / processors / exporters** | Named long-term participants without persona detail | §5 |
| **USDA / ICAC** | International public/industry data sources | §10 |

---

## Acronym Quick Reference

| Acronym | Expansion |
|---------|-----------|
| CCI | Cotton Corporation of India |
| DVA | Decision value added |
| IMD | India Meteorological Department |
| MSP | Minimum Support Price |
| NBFC | Non-Banking Financial Company |
| NCDEX | National Commodity & Derivatives Exchange |
| RBI | Reserve Bank of India |
| MI | Market Intelligence (mode) |
