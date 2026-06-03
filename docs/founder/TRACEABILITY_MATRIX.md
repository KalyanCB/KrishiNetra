# Traceability Matrix

**Source of truth:** `KrishiNetra_Founder_Thesis_Product_Spec_v5.docx` (v5.0)  
**Purpose:** Ensure architecture and implementation work retain alignment with founder intent.  
**Columns:** Requirement ID | Requirement | Source Section | Persona | Priority | Notes

**Priority legend:** P0 = Must (Phase 1 / strategic) | P1 = Should (Phase 1 or near-term) | P2 = Later phase | P3 = Future / unspecified detail

**Persona legend:** F = Farmer | T = Trader | E = Future enterprise | All = F + T | — = Not persona-specific

---

## Vision & Hypothesis

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-001 | Product must answer "What should I do next?" not only today's price | §1 | All | P0 | Core thesis |
| REQ-002 | Combine market intelligence with personal context, liquidity, financing, explainable reasoning | §1 | All | P0 | Central hypothesis |
| REQ-003 | Long-term vision: intelligence layer for farmers, traders, ginners, processors, warehouses, lenders, exporters | §5 | — | P2 | Phase 1 narrows to cotton F+T |

---

## Strategic Decisions (§2)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-010 | Cotton-first commodity validation | §2 D1 | All | P0 | FD-001 |
| REQ-011 | Recommendations account for net realized value (carry, liquidity) | §2 D2 | All | P0 | FD-002 |
| REQ-012 | Must outperform futures-implied (hold-to-curve) before claiming value | §2 D3 | All | P0 | FD-003 |
| REQ-013 | Agentic AI with specialized agents by signal domain | §2 D4 | — | P0 | FD-004 |
| REQ-014 | Farmers remain free; monetization via traders/enterprise/ecosystem later | §2 D5 | F | P0 | FD-005 |
| REQ-015 | Forecasting and sell/hold logic deterministic; agents orchestrate/explain only | §2 D6 | — | P0 | FD-006; TC-001 |

---

## Market Problem & Economics (§3–§4)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-020 | Address gap in contextual decision intelligence, not information availability | §3 | All | P0 | |
| REQ-021 | Support farmer economics: harvest timing, loans, cash, storage, risk tolerance | §4 | F | P0 | Inputs in §8 |
| REQ-022 | Support trader economics: inventory financing, working capital, storage, portfolio exposure, expected return | §4 | T | P0 | Portfolio detail thin in v5 |
| REQ-023 | All recommendations evaluated on net value, not gross price movement | §4 | All | P0 | |

---

## Market Intelligence Mode (§7)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-030 | No registration required for Market Intelligence | §7 | All | P0 | FD-011 |
| REQ-031 | Provide current prices | §7 | All | P0 | |
| REQ-032 | Provide outlook and forecasts | §7 | All | P0 | |
| REQ-033 | Provide confidence | §7 | All | P0 | Display format OQ-002 |
| REQ-034 | Provide bullish/bearish factors | §7 | All | P0 | |
| REQ-035 | Provide supply/demand analysis | §7 | All | P0 | |
| REQ-036 | Purpose: validate intelligence engine independent of user adoption | §7 | — | P0 | |
| REQ-037 | Market Intelligence computed centrally per data refresh, shared all users | §7, §9 | — | P0 | FD-012; NFR-SCL-001 |

---

## Decision Mode (§8)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-040 | Accept inputs: commodity, quantity, storage access, liquidity need, financing profile, risk profile | §8 | All | P0 | |
| REQ-041 | Output Sell, Hold, Partial Sell, or Partial Hold | §8 | All | P0 | Partial quantity OQ-006 |
| REQ-042 | Always show net value after carry | §8 | All | P0 | |
| REQ-043 | Always provide reasoning with recommendation | §8 | All | P0 | |
| REQ-044 | Recommendation via deterministic net-of-carry math plus named rules | §8 | All | P0 | Not LLM |
| REQ-045 | Net hold value formula includes forecast price, current price, storage, financing, quality loss, risk adjustment | §8 | All | P0 | |
| REQ-046 | MSP/CCI floor rule when spot at/near MSP and CCI actively procuring | §8 | All | P0 | FD-008; "near" OQ-005 |
| REQ-047 | MSP/CCI rule in Decision layer, not buried in forecast model | §8 | All | P0 | NFR-AUD-003 |

---

## Agentic Architecture (§9)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-050 | Market agent: deterministic; prices, arrivals, regional strength | §9 | — | P0 | |
| REQ-051 | Weather agent: deterministic; rainfall, drought, production-risk | §9 | — | P0 | |
| REQ-052 | Policy agent: deterministic; MSP, CCI, export restrictions | §9 | — | P0 | |
| REQ-053 | Demand agent: deterministic; exports, mills, consumption | §9 | — | P0 | |
| REQ-054 | Futures agent: deterministic; curve, basis, open interest | §9 | — | P0 | |
| REQ-055 | Global agent: deterministic; international demand, inventories | §9 | — | P0 | |
| REQ-056 | Forecast agent: deterministic model; 30/60/90 outlook + probability bands | §9 | All | P0 | |
| REQ-057 | Decision agent: deterministic math + rules; net-of-carry recommendation | §9 | All | P0 | |
| REQ-058 | Explainability agent: LLM; structured → human reasoning | §9 | All | P0 | |
| REQ-059 | Conversation agent: LLM; NL Q&A on explanation | §9 | All | P0 | |
| REQ-060 | Structured signal: value, direction, magnitude, confidence, as-of timestamp | §9 | — | P0 | Signal contract |
| REQ-061 | Domain agents never emit free text to Decision layer | §9 | — | P0 | |
| REQ-062 | No LLM in prediction or decision path | §9 | — | P0 | |
| REQ-063 | Forecast and decision are pure functions of data-as-of-date | §9 | — | P0 | Backtest dependency |
| REQ-064 | Per-user Decision: net-of-carry math + one explanation pass only | §9 | All | P0 | Cost constraint |

---

## Data Strategy (§10–§12)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-070 | Ingest public sources: Agmarknet, eNAM, IMD, Ag Ministry, USDA, ICAC | §10 | — | P0 | |
| REQ-071 | Ingest commercial: futures feeds, industry reports | §10 | — | P0 | |
| REQ-072 | Capture proprietary: decision sessions, outcomes, intent, inventory, warehouse occupancy | §10 | F,T | P0–P2 | Phased entities §15 |
| REQ-073 | Commodity registry defines price/arrival/demand/policy/weather/quality/storage/horizon per commodity | §11 | — | P0 | |
| REQ-074 | Cotton as reference implementation in registry | §11 | — | P0 | |
| REQ-075 | Cotton signals: arrivals, futures curve, MSP, CCI, mills, exports, weather, acreage, global inventories | §12 | — | P0 | Acreage agent mapping ambiguous |
| REQ-076 | Cotton outputs: 30/60/90 outlooks with confidence bands | §12 | All | P0 | |

---

## Forecasting & Trust (§13–§14)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-080 | Optimize for economically useful recommendations, not max accuracy | §13 | — | P0 | |
| REQ-081 | Evaluate directional accuracy, calibration, stability, decision value added | §13 | — | P0 | |
| REQ-082 | Benchmark: hold-to-futures-curve | §13 | — | P0 | |
| REQ-083 | Decision value added is primary; accuracy secondary | §13 | — | P0 | FD-009 |
| REQ-084 | Trust: calibration, stability, data quality, transparency, outcome tracking | §14 | All | P0 | |
| REQ-085 | Explain Why, what could go wrong, which assumptions matter | §14 | All | P0 | |

---

## Data Model Entities (§15)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-090 | Core entities Phase 1: Commodity, Region, Price, Arrival, Forecast, Recommendation, User Context, Decision Session, Outcome | §15 | All | P0 | Conceptual only per task rules |
| REQ-091 | Future entities: Inventory, Warehouse, Financing, Marketplace Transaction | §15 | E,T,F | P2–P3 | Roadmap phases |

---

## Founder Architecture Intent (§16) — Traceability Only

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-095 | Layer flow intent: ingestion → feature store → registry → orchestration → forecast → explainability → decision → APIs → dashboards | §16 | — | P1 | Descriptive; not implementation spec |
| REQ-096 | Commodity-configurable architecture | §16 | — | P0 | |
| REQ-097 | Structured signals between agents; deterministic core isolated from LLM | §16 | — | P0 | v5 note |
| REQ-098 | Market Intelligence precomputed per refresh | §16 | — | P0 | |

---

## Validation (§17)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-100 | Backtest three strategies: sell immediately, hold-to-curve, KrishiNetra | §17 | — | P0 | |
| REQ-101 | Measure net value added after carry | §17 | — | P0 | |
| REQ-102 | Promote recommendations only if KrishiNetra consistently adds value | §17 | — | P0 | Threshold OQ-008 |
| REQ-103 | Backtest valid only if deterministic path reproducible | §17 | — | P0 | |

---

## Flywheel & Monetization (§18–§19)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-110 | Flywheel: context → recommendation → outcome → calibration → trust → usage | §18 | All | P0 | Phase 1 start |
| REQ-111 | Build proprietary dataset unavailable publicly | §18 | — | P0 | |
| REQ-112 | Farmers free | §19 | F | P0 | |
| REQ-113 | Traders free initially; later subscription for advanced intelligence | §19 | T | P0/P2 | |
| REQ-114 | Future monetization: enterprise, warehouse, financing, marketplace | §19 | E | P3 | |

---

## Roadmap (§20)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-120 | Phase 1: Cotton intelligence + decision engine | §20 | F,T | P0 | |
| REQ-121 | Phase 2: Personalization + inventory registration | §20 | F,T | P2 | |
| REQ-122 | Phase 3: Behavioral learning + intent capture | §20 | F,T | P2 | |
| REQ-123 | Phase 4: Warehouse integration | §20 | — | P3 | |
| REQ-124 | Phase 5: Financing | §20 | F,T | P3 | Trigger OQ-003 |
| REQ-125 | Phase 6: Marketplace | §20 | — | P3 | |
| REQ-126 | Phase 7: Additional commodities by structure (storable, liquid futures, price floor) | §20 | All | P3 | FD-010; exclude mirchi |

---

## Risks & Mitigations (§21)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-130 | Curve as bar before UX scale | §21 | — | P0 | Mitigation |
| REQ-131 | Net-of-carry framing and partial-sell defaults for liquidity | §21 | F | P0 | |
| REQ-132 | Calibration, stability, conservative defaults for trust | §21 | All | P0 | |
| REQ-133 | Basis modeling + futures feed for Agmarknet gaps | §21 | — | P0 | |
| REQ-134 | Legal review: avoid investment advice; financing regulatory scope | §21 | — | P0 | OQ-009 |
| REQ-135 | Mitigate agentic non-reproducibility and cost via deterministic core, signals, precompute | §21 | — | P0 | |

---

## Open / Provisional (§22)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-140 | Daily data cadence with stability-gated recommendation flips | §22 | All | P1 | Working answer; field test OQ-001 |
| REQ-141 | Resolve trust score display format | §22 | All | P1 | OQ-002 |
| REQ-142 | Resolve financing introduction trigger | §22 | F,T | P3 | OQ-003 |

---

## v5 Changes (Document Meta)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-150 | Classify agents as deterministic services vs LLM components | Changes v5 | — | P0 | |
| REQ-151 | Restore MSP/CCI floor as named rule | Changes v5 | All | P0 | |
| REQ-152 | Resolve min accuracy, update freq, next commodity into spec | Changes v5 | — | P0 | See §13, §8, §20 |

---

## Persona-Specific Requirements (§6)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| REQ-160 | Farmer: decision intelligence | §6 | F | P0 | |
| REQ-161 | Trader: portfolio intelligence | §6 | T | P0 | Detail TBD |
| REQ-162 | Future enterprise: procurement and inventory intelligence | §6 | E | P3 | |

---

## Non-Functional Traceability (Cross-Reference)

| Requirement ID | Requirement | Source Section | Persona | Priority | Notes |
|----------------|-------------|----------------|---------|----------|-------|
| NFR-TRC-001 | Historical recommendation reproducibility | §9, §17 | — | P0 | See NON_FUNCTIONAL_REQUIREMENTS.md |
| NFR-TRS-001 | Trust framework components | §14 | All | P0 | |
| NFR-SCL-001 | Zero marginal MI cost per user | §7, §9 | — | P0 | |
| NFR-CAL-001 | DVA-primary evaluation | §13 | — | P0 | |

---

## Decision & Constraint Cross-Reference

| Requirement ID | Founder Decision ID | Constraint ID |
|----------------|---------------------|---------------|
| REQ-010 | FD-001 | PC-001 |
| REQ-011 | FD-002 | PC-009 |
| REQ-012 | FD-003 | PC-006 |
| REQ-015 | FD-006 | TC-001, TC-002 |
| REQ-046 | FD-008 | DC-007 |
| REQ-037 | FD-012 | CC-001, TC-007 |
| REQ-060 | FD-013 | TC-003, TC-004 |
| REQ-134 | FD-031 | RC-001, RC-002 |

---

## Coverage Summary

| Section | Requirement IDs | Count |
|---------|-----------------|-------|
| §1 Vision | REQ-001–003 | 3 |
| §2 Strategic | REQ-010–015 | 6 |
| §3–§4 Economics | REQ-020–023 | 4 |
| §7 MI Mode | REQ-030–037 | 8 |
| §8 Decision | REQ-040–047 | 8 |
| §9 Agents | REQ-050–064 | 15 |
| §10–§12 Data | REQ-070–076 | 7 |
| §13–§14 Forecast/Trust | REQ-080–085 | 6 |
| §15 Entities | REQ-090–091 | 2 |
| §16 Architecture intent | REQ-095–098 | 4 |
| §17 Validation | REQ-100–103 | 4 |
| §18–§19 Business | REQ-110–114 | 5 |
| §20 Roadmap | REQ-120–126 | 7 |
| §21 Risks | REQ-130–135 | 6 |
| §22 Open | REQ-140–142 | 3 |
| v5 / Personas | REQ-150–162 | 13 |
| **Total functional/trace rows** | | **~101** |

---

## Ambiguities & Contradictions Log

| ID | Type | Description | Affected REQ |
|----|------|-------------|--------------|
| AMB-001 | Ambiguity | "At or near" MSP floor undefined | REQ-046 |
| AMB-002 | Ambiguity | Partial sell/hold quantity logic undefined | REQ-041 |
| AMB-003 | Ambiguity | Acreage signal agent ownership | REQ-075 |
| AMB-004 | Ambiguity | "Consistently adds value" backtest threshold | REQ-102 |
| AMB-005 | Ambiguity | Trader portfolio intelligence vs per-session decision | REQ-161, REQ-022 |
| AMB-006 | Provisional | Stability gating / daily cadence needs field testing | REQ-140 |
| CON-001 | Tension | §16 lists full stack; Phase 1 scope is cotton intelligence + decision only | REQ-095 vs REQ-120 |
| CON-002 | Resolved v5 | Min accuracy question closed in favor of DVA backtest | REQ-083 |

---

## How to Use This Matrix

1. Every architecture or implementation artifact should map to one or more **Requirement IDs**.
2. **Founder Decision IDs** (`FOUNDER_DECISIONS.md`) provide rationale for non-negotiable boundaries (especially REQ-015, REQ-046, REQ-037).
3. **Open Questions** (`OPEN_QUESTIONS.md`) block finalization of rows flagged in Ambiguities Log.
4. Do not add requirements not traceable to v5 without founder review.
