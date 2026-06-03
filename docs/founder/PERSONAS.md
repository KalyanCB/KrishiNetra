# Personas

**Source of truth:** `KrishiNetra_Founder_Thesis_Product_Spec_v5.docx` (v5.0)

---

## Persona Overview

| Persona | Phase | Primary mode(s) | Monetization (per spec) |
|---------|-------|-----------------|-------------------------|
| Farmer | Phase 1 focus | Market Intelligence, Decision Mode | Free |
| Trader | Phase 1 focus | Market Intelligence, Decision Mode (portfolio intelligence) | Free initially; subscription later for advanced intelligence |
| Future enterprise | Post–Phase 1 | Procurement and inventory intelligence (not detailed in Phase 1) | Enterprise intelligence (§19 future) |

Long-term participants also named in vision (§5) but **not developed as personas** in v5: ginners, processors, warehouses, lenders, exporters. These map to later roadmap phases (warehouse, financing, marketplace) rather than Phase 1 persona definitions.

---

## P-001 — Farmer

### Description

Agricultural producer participating in cotton markets. Primary Phase 1 user. Needs contextual decision intelligence—not raw prices alone. Often faces liquidity-driven selling at harvest rather than market-timing optimization.

### Goals

| Goal | Spec basis |
|------|------------|
| Improve realized outcomes from inventory/selling decisions | §1 hypothesis, §4 farmer economics |
| Understand what to do next (sell, hold, partial actions) with explainable reasoning | §1, §8 |
| See recommendations in net terms after carry, storage, financing, and risk | §2, §8 |
| Access market intelligence without registration friction | §7 |
| Trust recommendations through calibration, transparency, and outcome tracking | §14 |

### Problems

| Problem | Spec basis |
|---------|------------|
| Sells at harvest due to liquidity requirements, not market expectations | §3 |
| Lacks decision support combining market intelligence with personal context | §3 |
| Cash constraints make theoretically correct "hold" recommendations unactionable | §21 liquidity risk |
| Risk of trust collapse after a single bad/localized wrong hold call | §21 |
| Limited rigorous framework connecting harvest timing, loans, cash needs, storage, risk tolerance | §4 |

### Decisions Supported

| Decision type | Output (§8) | Context inputs (§8) |
|---------------|---------------|---------------------|
| Sell vs hold vs partial actions on cotton inventory | Sell, Hold, Partial Sell, Partial Hold | Commodity, quantity, storage access, liquidity need, financing profile, risk profile |
| Interpretation of 30/60/90-day cotton outlook | Market Intelligence Mode | No registration; shared central outlook |
| Policy-floor-aware hold calculus | MSP/CCI floor rule when applicable | §8 |

### Success Metrics

| Metric | Spec basis | Notes |
|--------|------------|-------|
| Decision value added vs sell-at-harvest and hold-to-futures-curve (net of carry) | §13, §17 | Primary economic success measure |
| Directional accuracy, calibration, stability | §13, §14 | Secondary to decision value added |
| Adoption and sustained usage despite free tier | §18 flywheel | Usage growth enables proprietary data |
| Trust maintenance (calibration, conservative defaults) | §14, §21 | Qualitative + outcome tracking |
| Outcome capture from decision sessions feeding calibration | §18 | Phase 1 flywheel start |

**Not specified in v5:** farmer-specific KPIs (MAU, NPS, revenue)—farmers are explicitly not monetized in Phase 1.

---

## P-002 — Trader

### Description

Market participant holding cotton inventory with portfolio and working-capital exposure. Phase 1 focus alongside farmers. Needs portfolio intelligence and risk-adjusted framing for inventory decisions.

### Goals

| Goal | Spec basis |
|------|------------|
| Improve net realized value across inventory positions | §2, §4 trader economics |
| Apply rigorous risk-adjusted framework to inventory holds | §3 |
| Access cotton market intelligence (prices, outlook, supply/demand, confidence) | §7, §12 |
| Eventually access advanced intelligence via subscription | §19 |

### Problems

| Problem | Spec basis |
|---------|------------|
| Holds inventory without rigorous risk-adjusted framework | §3 |
| Working-capital, storage, and portfolio exposure not integrated in typical price/news tools | §4 |
| Same trust and data-quality constraints as farmers | §14, §21 |
| Forecast failing to beat futures curve erodes core value proposition | §21 |

### Decisions Supported

| Decision type | Output | Context |
|---------------|--------|---------|
| Inventory sell/hold/partial recommendations (net of carry) | §8 four recommendation types | Full Decision Mode inputs |
| Portfolio-level intelligence (implied by "portfolio intelligence" label) | §6 | **Detail not specified in v5**—Phase 1 may be per-position/session until Phase 2 personalization/inventory |
| Market Intelligence for cotton | §7 | Shared precomputed outlook |

### Success Metrics

| Metric | Spec basis |
|--------|------------|
| Net value added vs benchmarks in backtest and live outcomes | §17 |
| Decision value added (primary); accuracy secondary | §13 |
| Willingness to convert to paid advanced intelligence (future) | §19 |
| Calibration and stability of calls | §14 |

---

## P-003 — Future Enterprise

### Description

Future participant focused on **procurement and inventory intelligence** (§6). Not a Phase 1 delivery persona; represents enterprise buyers/processors with inventory and procurement optimization needs.

### Goals

| Goal | Spec basis |
|------|------------|
| Procurement and inventory intelligence at enterprise scale | §6, §5 long-term vision |
| Leverage KrishiNetra intelligence layer across inventory decisions | §5 |

### Problems

| Problem | Spec basis |
|---------|------------|
| Not elaborated in v5 beyond label | §6 only |

### Decisions Supported

| Area | Spec basis |
|------|------------|
| Procurement timing and inventory optimization (implied) | §6 |
| Future entities: Inventory, Warehouse, Financing, Marketplace Transaction | §15, §20 Phases 2–6 |

**Gap:** No Phase 1 inputs, outputs, or recommendation types defined for enterprise.

### Success Metrics

| Metric | Spec basis |
|--------|------------|
| Enterprise intelligence monetization (future) | §19 |
| **Not otherwise specified** | — |

---

## Persona × Product Mode Matrix

| Persona | Market Intelligence (no registration) | Decision Mode (context required) | Phase 1 |
|---------|--------------------------------------|----------------------------------|---------|
| Farmer | Yes | Yes | Primary |
| Trader | Yes | Yes | Primary |
| Future enterprise | Not specified | Not specified | No |

---

## Persona × Roadmap Alignment

| Phase | Farmer | Trader | Future enterprise |
|-------|--------|--------|-------------------|
| 1 — Cotton intelligence + decision engine | ✓ | ✓ | — |
| 2 — Personalization, inventory registration | Enhanced context | Enhanced context | — |
| 3 — Behavioral learning, intent capture | Intent data | Intent data | — |
| 4 — Warehouse integration | — | — | Possible overlap |
| 5 — Financing | Financing profile inputs mature | — | Partnership surface |
| 6 — Marketplace | — | — | Likely |
| 7 — Additional commodities | Beyond cotton | Beyond cotton | TBD |
