# DS-001 — Commercial Futures Feed Vendor Decision (REQ-071)

**Date:** 2026-06-03  
**Workstream:** E — KDO research (no code)  
**Status:** Complete — awaiting founder sign-off  
**Inputs (read-only):** [COTTON_DATA_SOURCE_VALIDATION.md](./COTTON_DATA_SOURCE_VALIDATION.md), `docs/founder/` (REQ-071, DA-002, DD-005), [TDS-007](../tds/TDS-007-Forecast-Architecture.md) §3–5 (Futures features), [IMPLEMENTATION_READINESS_REVIEW.md](../reviews/IMPLEMENTATION_READINESS_REVIEW.md) (DS-001)

---

## 1. Executive Summary

Phase 1 cotton intelligence requires a **licensed** commercial futures feed (REQ-071) to power the Futures Agent, basis features (`basis_spot_futures`, `basis_futures_spot`), hold-to-curve benchmark (REQ-082), and forecast gate G6 (Futures + Market ≥ 99% days). Public Agmarknet spot alone does not satisfy DD-005.

**Primary path:** **NCDEX KAPAS** (Indian cotton/kapas complex) via an **NCDEX-authorized EOD/delayed data vendor** (domestic sublicensor), ingested as **EOD bhav copy + OI** on a **daily batch** cadence (DA-008, TDS-005).

**Fallback path:** **Direct NCDEX NDU — EOD Bhav Copy** license (~₹15,000/year domestic) with in-house UDiFF/CSV ingest, until a vendor API contract is executed; use **public bhav download** only for non-production dev with explicit legal waiver.

**Defer for Phase 1:** Bloomberg/Refinitiv-class terminals, NCDEX/MCX **real-time** direct feeds, and **dual-exchange** integration (NCDEX + MCX).

---

## 2. Product Requirements (from frozen baseline)

| ID | Requirement | Implication for vendor choice |
|----|-------------|-------------------------------|
| REQ-071 | Ingest commercial futures feeds | Exchange NDU or authorized sub-license; not REQ-070 public scraping |
| REQ-075 / TDS-007 | Futures curve, basis, OI | Near-month price, curve slope, OI change; **EOD minimum** |
| REQ-082 / FD-003 | Hold-to-futures-curve benchmark | Same curve as-of T; no revised history in backtest |
| REQ-133 / FD-030 | Basis vs Agmarknet | Concurrent licensed futures + mandi spot |
| DA-002 | Commercial futures obtainable | Contract + NDU path must be budgeted |
| DA-008 | Daily refresh adequate | Real-time not required Phase 1 |
| TDS-007 G6 | Futures + Market agents ≥ 99% days | Reliable EOD delivery SLO more important than tick latency |

**Futures features (TDS-007 §5.2):** `curve_slope`, `curve_level_near`, `open_interest_change`, `basis_futures_spot`, `carry_implied_30/60/90`.

---

## 3. Venue Context (NCDEX vs MCX)

| Venue | Cotton-relevant products | Phase 1 role |
|-------|-------------------------|--------------|
| **NCDEX** | KAPAS (Shankar kapas), 29 MM Cotton, cotton wash oil derivatives | **Primary** — agricultural cotton complex; ~80% India ag-deriv share cited by NCDEX/TradingView |
| **MCX** | Kapas futures; **Cotton** futures (revised specs from Nov 2025 expiries per MCX/TRD/306/2025) | **Secondary** — monitor liquidity; do not dual-integrate in Phase 1 |

Track C concluded: treat NCDEX as one licensed venue; pick **one commercial aggregator** to avoid dual-exchange cost and integration ([COTTON_DATA_SOURCE_VALIDATION.md](./COTTON_DATA_SOURCE_VALIDATION.md) §3.4).

**Liquidity note:** NCDEX KAPAS can show **thin OI** on active months (e.g. OI in tens of contracts on live quotes). Product should store `futures_feed_ok` and confidence penalties when OI/volume below thresholds (TDS-006/TDS-011).

---

## 4. Option Comparison

### 4.1 NCDEX — Direct exchange license

| Dimension | Assessment |
|-----------|------------|
| **Cost (order of magnitude)** | **EOD Bhav Copy:** ₹15,000/year domestic (~$500 international). **20 min delayed:** ₹25,000/year. **2 min delayed:** ₹6,00,000/year. **Level 1 real-time (software product):** ₹20,00,000/year + variable per-user fees. **Enterprise EOD/non-display bundle:** ₹5,00,000/year (domestic). Historical tick/all-commodity: ₹1,00,000–₹2,50,000/year per product tier. |
| **Licensing** | NDU (Non-Display Usage) agreement; annual advance billing; non-display fees apply when data feeds backend/algo use ([NCDEX tariffs](https://ncdex.com/tech/tariffs)). Redistribution/display rules separate. |
| **Historical depth** | Per-year historical order/trade books (paid); public **historical bhav** UI download (pre/post UDiFF Jul 2024); contract inception varies by product. |
| **Refresh frequency** | EOD bhav after session; delayed tiers 2–20 min; real-time L1/L2. |
| **Integration complexity** | **Medium** — file-based EOD (CSV/XLS UDiFF) or vendor multicast if upgrading; no public REST API on exchange site; ops must handle holidays/circulars. |

**Sources:** [NCDEX Data Feed Tariff](https://ncdex.com/tech/tariffs), [Bhav Copy](https://ncdex.com/index.php/markets/bhavcopy), [Type of subscribers / Non-Display](https://ncdex.com/index.php/data-feed/type_of_subscribers).

---

### 4.2 MCX — Direct exchange license

| Dimension | Assessment |
|-----------|------------|
| **Cost (order of magnitude)** | Published **Data Feed Price List** (domestic/international, effective Jul 2024) — same order of magnitude as NCDEX for EOD/delayed/real-time tiers; plus **connectivity:** ₹1,00,000/year (internet) or ₹1,50,000/year (leased line) for real-time pipe ([MCX medium of delivery](https://www.mcxindia.com/technology/datafeed/medium-of-delivery)). |
| **Licensing** | Vendor/redistributor/member agreements; websites may show **delayed only**; resale prohibited ([MCX who can subscribe](https://www.mcxindia.com/technology/datafeed/who-can-subscribe-to-datafeed)). |
| **Historical depth** | Historical tick/order book on request, **minimum one year** blocks; bhav copy EOD. |
| **Refresh frequency** | Real-time L1/L2, delayed 1–20 min, EOD bhav. |
| **Integration complexity** | **Medium–High** — separate feed stack from NCDEX; dual exchange doubles compliance and ingest. |

**Sources:** [MCX Datafeed overview](https://www.mcxindia.com/technology/datafeed), [Data feed product and charges](https://www.mcxindia.com/technology/datafeed/data-feed-product-and-charges).

---

### 4.3 Commercial aggregators (Bloomberg / Refinitiv LSEG class)

| Dimension | Assessment |
|-----------|------------|
| **Cost (order of magnitude)** | **Bloomberg Terminal:** ~$24,000–$27,000/user/year (industry benchmark). **Enterprise Data License / F&O bulk:** typically **$10,000–$100,000+**/year negotiated by scope ([Bloomberg Data License](https://www.bloomberg.com/professional/products/data/data-management/data-license/), [Vendr benchmark](https://www.vendr.com/marketplace/bloomberg)). **LSEG:** custom commodities/futures packages; India NCDEX/MCX often **exchange pass-through** fees on top ([LSEG futures data](https://www.lseg.com/en/data-analytics/financial-data/pricing-and-market-data/futures-data)). |
| **Licensing** | Global enterprise agreements; Indian exchange redistribution embedded or add-on; strict audit/display rules. |
| **Historical depth** | **Strong** — decades, global cross-asset; best for multi-commodity Phase 7 (MA-005). |
| **Refresh frequency** | Real-time through EOD; matches any Phase 1 need. |
| **Integration complexity** | **High** — proprietary identifiers (FIGI/RIC), entitlement setup, legal review, likely overkill for single-commodity daily cotton MI. |

**NCDEX authorized real-time vendors include:** Bloomberg, Refinitiv Asia, FactSet, ICE, Cogencis, IQN, Ticker Data ([authorized vendors](https://ncdex.com/index.php/data-feed/ncdex-authorized-data-feed-vendors)).

---

### 4.4 Authorized domestic EOD/delayed vendors (Accelpix, Accord, TradingView, etc.)

| Dimension | Assessment |
|-----------|------------|
| **Cost (order of magnitude)** | **Vendor SaaS/API:** roughly **₹2,000–₹90,000+/year** by symbol count and history (e.g. Accelpix published tiers ₹2,149–₹91,789/year) **plus** exchange pass-through/sub-license fees (often **not** included in list price). **Exchange EOD** reference: ₹15,000/year (NCDEX bhav) as floor for direct NDU. |
| **Licensing** | Vendor holds NCDEX/MCX authorization; subscriber bound to **no redistribution**, single-subscriber use, SEBI/exchange approval for simulators ([Accelpix T&C](https://accelpix.com/pix-apis/)). KrishiNetra needs **written sublicense** for backend non-display ingest. |
| **Historical depth** | Vendor-dependent (e.g. 5–12 years EOD on Accelpix pricing page); deep tick history costs extra. |
| **Refresh frequency** | EOD, 1-min, tick tiers; aligns with Phase 1 if EOD tier selected. |
| **Integration complexity** | **Low–Medium** — REST/WebSocket/Python APIs (where offered); vendor handles feed ops; **must** confirm NCDEX KAPAS + OI fields in API schema. |

**NCDEX EOD/delayed authorized vendors include:** Accelpix, Accord Fintech, Fusion Media (TradingView), Dion Global, Edelweiss Broking, Global Financial Datafeeds, etc. ([authorized vendors](https://ncdex.com/index.php/data-feed/ncdex-authorized-data-feed-vendors)).

**TrueData** (MCX-authorized example): exchange-approved API; pricing quote-based; exchange fees separate ([TrueData market APIs](https://www.truedata.in/market-data-apis)).

---

### 4.5 Alternative delayed / public feeds

| Dimension | Assessment |
|-----------|------------|
| **Cost** | **Public bhav pages:** ₹0 download ([NCDEX bhav copy](https://ncdex.com/index.php/markets/bhavcopy)). **TradingView delayed:** **Free** delayed charting for MCX/NCDEX on platform ([TradingView data coverage](https://in.tradingview.com/data-coverage/)) — **not** a substitute for REQ-071 backend ingest without vendor redistribution deal. **NCDEX research policy:** up to **2 GB/year** free for accredited academic research only — **not** commercial product ([research sharing](https://ncdex.com/index.php/data-feed/sharing-data-for-the-purpose-of-research-analysis)). |
| **Licensing** | Public download ≠ commercial NDU; automated scraping of portal **not** approved for production (Track C). TradingView/Fusion Media is authorized **vendor**, not an API you can scrape. |
| **Historical depth** | Public bhav: date-picker + historical section; gaps possible around UDiFF migration (Jul 2024). |
| **Refresh frequency** | EOD (post-close file drop). |
| **Integration complexity** | **Low technically / High legally** — CSV parser + scheduler; requires founder/legal sign-off for dev-only vs production. |

---

## 5. Summary Matrix

| Option | Annual cost (OM) | REQ-071 production-ready | Historical / OI | Refresh (Phase 1) | Integration |
|--------|------------------|----------------------------|-----------------|-------------------|-------------|
| NCDEX direct EOD NDU | **₹0.015–0.5M** | Yes (with NDU) | Good (bhav); deep books extra | EOD | Medium |
| MCX direct EOD | **₹0.015–0.5M+** | Yes (with agreement) | Good | EOD | Medium |
| NCDEX/MCX real-time direct | **₹2M–4.5M+** | Yes | Excellent | Real-time | High |
| Bloomberg / Refinitiv | **$10k–100k+** | Yes | Excellent | All | High |
| Domestic authorized vendor (EOD API) | **₹0.05–0.2M** vendor + exchange | Yes (with sublicense) | Good | EOD–1min | **Low–Medium** |
| Public bhav / TV delayed | **₹0** | **No** (prod) | Limited | EOD / delayed UI | Low |

*OM = order of magnitude, exclusive of taxes; vendor quotes required for binding budget.*

---

## 6. Recommendation

### 6.1 Primary path

**NCDEX KAPAS EOD** delivered through an **NCDEX-authorized EOD/delayed domestic vendor** (shortlist: **Accelpix**, **Accord Fintech**, **Global Financial Datafeeds**) with:

1. **Contract scope:** KAPAS futures + options chain fields needed for `curve_level_near`, `curve_slope`, `open_interest_change`; EOD bhav or 20-min delayed (not L1 real-time).
2. **Legal:** Written **non-display sublicense** for backend ingest into KrishiNetra observations (REQ-071); metadata `source=futures_feed`, `exchange=NCDEX`.
3. **Technical:** Daily batch job after NCDEX EOD file stability; map to `FuturesObservation` / agent inputs per TDS-006; `DataQualitySnapshot.futures_feed_ok`.
4. **Rationale:** Matches DA-008 daily cadence, minimizes cost vs real-time, single venue for cotton/kapas, API integration faster than direct multicast, satisfies Track C “one aggregator” guidance.

**Budget planning (Year 1):** **₹3–8 lakhs** all-in (vendor subscription + exchange pass-through + legal review), vs **₹20 lakhs+** for direct real-time software-product license.

### 6.2 Fallback path

1. **Immediate production-capable fallback:** **Direct NCDEX NDU — EOD Bhav Copy** (₹15,000/year domestic tariff line) + internal parser for UDiFF CSV/XLS ([tariffs](https://ncdex.com/tech/tariffs), [bhav copy](https://ncdex.com/index.php/markets/bhavcopy)). Lowest cost; no vendor API; ops owns file delivery.
2. **Sprint 0 / engineering unblock only (non-REQ-071):** Scheduled download of **public bhav** with founder/legal acknowledgment that MI published to users requires NDU before go-live.

**Do not use** NCDEX academic research 2 GB policy or TradingView free delayed charts as the production REQ-071 feed.

### 6.3 Explicitly out of scope Phase 1

| Item | Reason |
|------|--------|
| Bloomberg / Refinitiv enterprise | Cost and integration disproportionate to cotton-only daily MI |
| MCX parallel integration | Dual compliance; NCDEX KAPAS sufficient for Phase 1 registry |
| NCDEX/MCX real-time L1 | DA-008 daily batch; ₹20L+ license |
| Unlicensed scrapers | Exchange terms + DS-001 readiness blocker |

---

## 7. Founder / Program Actions

| # | Action | Owner |
|---|--------|-------|
| 1 | Approve **primary + fallback** paths above | Founder |
| 2 | Issue RFP to 2–3 NCDEX EOD authorized vendors (KAPAS EOD API + OI, sublicense terms, SLA) | Program / Ops |
| 3 | Parallel quote **NCDEX direct NDU EOD** for fallback pricing confirmation | Ops |
| 4 | Unblock E-03 ingest design: `futures_feed` registry string, observation schema, quality flags | E-03 |
| 5 | Revisit MCX Cotton liquidity post-launch (2025 contracts) before Phase 7 multi-commodity | Product |

---

## 8. DS-001 Resolution Status

| Field | Value |
|-------|-------|
| **Decision** | Primary: NCDEX EOD via authorized domestic vendor; Fallback: direct NCDEX EOD NDU |
| **Blocks removed when** | Signed NDU or vendor sublicense on file |
| **Still blocks** | E-03 production ingest, E-06 credible hold-to-curve bake-off until contract executed |

---

## 9. References

| Source | URL |
|--------|-----|
| NCDEX authorized vendors | https://ncdex.com/index.php/data-feed/ncdex-authorized-data-feed-vendors |
| NCDEX tariffs | https://ncdex.com/tech/tariffs |
| NCDEX bhav copy | https://ncdex.com/index.php/markets/bhavcopy |
| NCDEX KAPAS product | https://ncdex.com/index.php/products/KAPAS |
| NCDEX research data policy | https://ncdex.com/index.php/data-feed/sharing-data-for-the-purpose-of-research-analysis |
| MCX datafeed | https://www.mcxindia.com/technology/datafeed |
| MCX data charges | https://www.mcxindia.com/technology/datafeed/data-feed-product-and-charges |
| MCX Kapas | https://www.mcxindia.com/products/agro-commodities/kapas |
| TradingView NCDEX blog | https://www.tradingview.com/blog/en/ncdex-data-on-tradingview-35303/ |
| TradingView data coverage | https://in.tradingview.com/data-coverage/ |
| Accelpix pricing (indicative) | https://accelpix.com/pricing/ |
| Bloomberg Data License | https://www.bloomberg.com/professional/products/data/data-management/data-license/ |
| LSEG futures data | https://www.lseg.com/en/data-analytics/financial-data/pricing-and-market-data/futures-data |
| Internal: cotton validation | [COTTON_DATA_SOURCE_VALIDATION.md](./COTTON_DATA_SOURCE_VALIDATION.md) |
| Internal: readiness DS-001 | [IMPLEMENTATION_READINESS_REVIEW.md](../reviews/IMPLEMENTATION_READINESS_REVIEW.md) §9 |

---

## 10. Document Control

| Field | Value |
|-------|-------|
| Author | KDO Workstream E |
| Status | Complete — pending founder approval |
| Next review | After vendor RFP responses or NDU execution |
