# Cotton Data Source Validation — Phase 1 (Track C)

**Date:** 2026-06-03  
**Branch (intended):** `feature/cotton-data-research`  
**Product truth (read-only):** `docs/founder/` (DATA_DOMAINS, ASSUMPTIONS, TRACEABILITY_MATRIX), TDS-001, TDS-004, TDS-007, TDS-009, TDS-014 (E-03), E-02-S04 source name strings  
**Agent package (Global):** [ADR-005](../adrs/ADR-005-agent-package-naming.md) — `agents/global_signals/`  
**Epic consumer:** E-03 Ingestion & Observations (REQ-070 public; REQ-071 commercial futures separate)

---

## 1. Executive Summary

Phase 1 cotton ingestion assumes **DA-001** (public sources usable) and **DA-002** (commercial futures materially improve intelligence). This validation confirms that **USDA** and **ICAC** are the strongest public global/demand paths; **Agmarknet** is viable but needs an explicit government data contract (OGD/portal) and lag handling (**DC-001**, **FD-030**); **eNAM** is secondary with **no documented public API**; **IMD** splits between near-real-time APIs (operational constraints) and licensed historical DSP; **NCDEX** is **not** a REQ-070 public source—it is a **commercial futures candidate** (REQ-071) with exchange licensing, overlapping **MCX** cotton/kapas products.

**E-03 top risks:** (1) undocumented commercial futures vendor (DS-001), (2) Agmarknet lag/gaps, (3) eNAM/IMD programmatic access and licensing for production automation, (4) ICAC/USDA automation vs dashboard-only workflows.

---

## 2. Agent Mapping Reference

| Agent | Package path (ADR-005) | Primary Phase 1 sources (founder/TDS) |
|-------|------------------------|--------------------------------------|
| Market | `agents/market/` | Agmarknet, eNAM |
| Weather | `agents/weather/` | IMD (+ acreage inputs per TDS-004) |
| Policy | `agents/policy/` | Agriculture Ministry (not in this doc’s source list) |
| Demand | `agents/demand/` | USDA, ICAC, industry reports (commercial) |
| Futures | `agents/futures/` | Commercial futures feed (REQ-071); NCDEX evaluated as candidate |
| Global | `agents/global_signals/` | USDA, ICAC |

Cotton registry (**TDS-009 §11.1**): required agents **Market, Futures**; optional Weather, Policy, Demand, Global.

---

## 3. Source Validations

### 3.1 Agmarknet

| Dimension | Assessment |
|-----------|------------|
| **Availability** | **Yes** — national mandi daily prices and arrivals; cotton listed in commodity-wise reports. Portal “Agmarknet 2.0” with daily price/arrival reports. |
| **Access method** | **Multi-path:** (1) Web UI — commodity/market-wise daily reports with Excel export ([India Gov Services Portal](https://services.india.gov.in/service/detail/check-agriculture-commodity-and-market-wise-daily-reports-1), [Commodity-wise report](https://agmarknet.gov.in/PriceAndArrivals/CommodityWiseDailyReport.aspx)); (2) **OGD India (preferred for E-03)** — catalog “Current daily price… (Mandi)” with zip bulk download and **Data API** via `api.data.gov.in` (resource UUID `9ef84268-d588-465a-a308-a864a43d0070`; register API key for limits beyond demo queries) ([catalog](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi), [API resource page](https://data.gov.in/resources/current-daily-price-various-commodities-various-markets-mandi/api)); (3) India Data Portal CKAN mirror for APMC arrivals/prices ([India Data Portal](https://ckandev.indiadataportal.com/dataset/apmc-arrivals-and-prices)). No first-party REST API documented on `agmarknet.gov.in` itself. |
| **Refresh frequency** | **Daily** (mandi reporting cycle); aligns with Phase 1 daily MI precompute (**DA-008**). Actual latency varies by mandi/state (**DC-001**). |
| **Historical depth** | **Multi-year** via portal date selectors and OGD bulk archives; Agmarknet 2.0 advertises 365-day farmer-facing reports ([agmarknet.gov.in](https://www.agmarknet.gov.in/home)). Full national history typically requires OGD zip backfills or DACNET statistical reports. |
| **Licensing concerns** | Released under **National Data Sharing and Accessibility Policy (NDSAP)** on OGD ([data.gov.in catalog](https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi)). Attribution and government open-data terms apply; confirm redistribution/display in product legal review. Scraping the ASP.NET portal without API is fragile and may violate site terms—prefer OGD/API channel. |
| **Confidence** | **Medium** — Strong product fit (Market Agent price + arrival). Downgraded vs High because: (a) founder-documented lag/gaps (**DC-001**, **FD-030**), (b) programmatic path should be locked to **OGD Catalog API or official DMI channel**, not unofficial aggregators. |

**Agent mapping:** **Market** — `PriceObservation`, `ArrivalObservation` (TDS-007 §3, DATA_DOMAINS DD-001).

**REQ traceability:** REQ-070, REQ-075 (arrivals), REQ-133 (basis mitigation).

---

### 3.2 eNAM (National Agriculture Market)

| Dimension | Assessment |
|-----------|------------|
| **Availability** | **Yes** — live/min/max/modal prices and mandi trade context for notified commodities; cotton/kapas-related flows depend on onboarded APMCs. |
| **Access method** | **Dashboard/UI only** for price discovery: [e-NAM Live Price](https://enam.gov.in/web/dashboard/live_price), [eNAM home](https://enam.gov.in/). Mobile app exposes price/arrival viewing ([PIB eNAM release](https://www.pib.gov.in/PressReleasePage.aspx?lang=1&PRID=2251543&reg=3)). **No public machine-readable API** documented; independent review of Indian ag data platforms notes eNAM/Krishi-DSS lack unified open APIs ([arXiv:2603.23289](https://arxiv.org/html/2603.23289v2)). |
| **Refresh frequency** | **Intra-day / daily** on live dashboard (trading-day dependent); suitable as **secondary** confirmatory series, not primary low-latency feed. |
| **Historical depth** | **Limited via UI** (date-range filters on dashboard); no confirmed bulk historical API. Historical work likely requires stored snapshots from daily ingest or Agmarknet overlap. |
| **Licensing concerns** | Government-operated public dashboard; automated scraping not documented—legal/ops review required before production scraper. Prefer manual/API channel from SFAC if obtainable via data request. |
| **Confidence** | **Medium–Low** — Supports **DA-001** for human-visible prices; **Low for automated E-03** until access mode is contractual (API, file drop, or licensed vendor). |

**Agent mapping:** **Market** — secondary price series (TDS-007: “Secondary price”; TDS-001).

**REQ traceability:** REQ-070.

---

### 3.3 IMD (India Meteorological Department)

| Dimension | Assessment |
|-----------|------------|
| **Availability** | **Yes** — rainfall, warnings, nowcast; district/state rainfall aggregates suitable for production-risk signals. |
| **Access method** | **Two tiers:** (1) **Public REST APIs** — documented reference incl. district-wise rainfall `https://api.imd.gov.in/api/v1/districtrainfall` ([IMD API Reference](https://api.imd.gov.in/public/api_reference.html)); operational notes mention **IP whitelisting** and issue ticketing ([IMD APIs page](https://mausam.imd.gov.in/responsive/apis.php)). (2) **Historical station/gridded data** — [IMD Data Service Portal (DSP)](https://dsp.imdpune.gov.in/) requires **enrolment**, identity documentation, and **Certificate of Undertaking** (non-commercial / no third-party transfer without approval). |
| **Refresh frequency** | **Daily to sub-daily** for rainfall APIs; forecast endpoints on separate cadence. Matches Weather Agent daily refresh (TDS-004). |
| **Historical depth** | **Long archive** via DSP (paid/free categories by user type); API tier focuses on recent operational windows—confirm retention per endpoint. |
| **Licensing concerns** | DSP terms restrict commercial use and redistribution without written IMD approval ([DSP portal](https://dsp.imdpune.gov.in/)). Public API use still requires compliance with attribution, whitelisting, and rate/availability SLOs. **Acreage** is not an IMD product—founder lists acreage under cotton model; TDS-004 assigns acreage to Weather Agent with separate Ministry/statistical sources (out of scope for “IMD-only”). |
| **Confidence** | **Medium** — Adequate for Weather Agent rainfall/drought sub-signals. Downgraded for: whitelisting ops, DSP licensing for deep backtest, acreage needing non-IMD ingest. |

**Agent mapping:** **Weather** — rainfall, drought indices; acreage sub-component may be **partial** without Ag Ministry/Census linkage (TDS-004 failure: omit acreage, reduce confidence).

**REQ traceability:** REQ-070, REQ-051, REQ-075.

---

### 3.4 NCDEX (National Commodity & Derivatives Exchange)

| Dimension | Assessment |
|-----------|------------|
| **Availability** | **Yes** for Indian commodity derivatives — **KAPAS** and related cotton complex contracts ([NCDEX KAPAS product](https://ncdex.com/index.php/products/KAPAS)). **MCX** also lists Kapas and, from Nov 2025 onward, revised **Cotton** futures ([MCX Kapas](https://www.mcxindia.com/products/agro-commodities/kapas)) — product truth does not mandate a single exchange. |
| **Access method** | **Commercial only** — NCDEX Data Feed (real-time, delayed, EOD bhav copy, historical order/trade books) via **NDU agreement** and tariffs ([NCDEX data feed overview](https://ncdex.com/index.php/data-feed/ncdex-authorized-data-feed-vendors), [tariffs](https://ncdex.com/tech/tariffs)). Authorized vendors include Bloomberg, Refinitiv, TradingView, etc. ([authorized vendors](https://ncdex.com/index.php/data-feed/ncdex-authorized-data-feed-vendors)). **Research** path: limited free basket (≤2 GB/year) with application ([research sharing policy](https://ncdex.com/index.php/data-feed/sharing-data-for-the-purpose-of-research-analysis)). |
| **Refresh frequency** | **Real-time to EOD** depending on license tier; Phase 1 daily MI needs at minimum **EOD bhav copy** (tariff lists EOD domestic ~₹15,000/year class). |
| **Historical depth** | **Per-year historical** order/trade book products (paid); suitable for DVA/backtest once licensed. |
| **Licensing concerns** | **Exchange market data license required**; display redistribution rules in NDU; not interchangeable with REQ-070 “public” sources. Research free tier **not** for commercial product without separate agreement. |
| **Confidence** | **Medium (as futures source) / N/A for REQ-070** — Technically viable for **Futures Agent** curve/basis/OI (**REQ-071**, **FD-003**, **FD-030**). **Low for immediate E-03** without vendor selection (**DS-001**). Not listed in TDS-001 §4.1 public table; founder mentions NCDEX only as **Phase 7 follow-on commodity** example (**MA-005**), not Phase 1 cotton futures mandate. |

**Agent mapping:** **Futures** — commercial feed candidate (same role as generic “futures feeds” in DATA_DOMAINS DD-005). **Not** Global/Market unless mapping spot indices from NCDEX spot price products (separate tariff line).

**REQ traceability:** REQ-071 (primary); indirectly REQ-133, REQ-054, REQ-082 via Futures Agent.

**Recommendation for E-03:** Treat NCDEX as **one licensed venue** alongside MCX; pick **one commercial aggregator** (vendor list on NCDEX site) to avoid dual-exchange integration in Phase 1 unless registry explicitly lists both.

---

### 3.5 USDA (Foreign Agricultural Service / WASDE ecosystem)

| Dimension | Assessment |
|-----------|------------|
| **Availability** | **Yes** — global cotton in Production, Supply and Distribution (PSD) and WASDE-aligned series. |
| **Access method** | **FAS Open Data Services** REST portal (`apps.fas.usda.gov/opendataweb`, API key signup) for commodity series ([FAS Databases and Applications](https://www.fas.usda.gov/data/databases-applications)); **PSD Online** UI/downloads ([PSD Online](https://apps.fas.usda.gov/psdonline/app/index.html#/app/home)); **PSD SOAP** `getDatabyCommodity` (country/attribute/year from 2000 forward) at [PSDExternalAPIService](https://apps.fas.usda.gov/PSDExternalAPIService/svcPSD_AMIS.asmx?op=getDatabyCommodity). Cotton also in weekly **Export Sales** (GATS/Open Data where keyed). |
| **Refresh frequency** | **Monthly** (WASDE/PSD release cycle); slower than daily mandi data—matches TDS-007 “slower cadence” for USDA/ICAC. |
| **Historical depth** | **Decades** at country/commodity level in PSD; suitable for global inventory z-score features (TDS-007 §5). |
| **Licensing concerns** | **U.S. government open data** — standard attribution; verify API terms on FAS portal for redistribution. No exchange-style market data license. |
| **Confidence** | **High** — Best-documented public API path for **Demand** and **Global** agents; aligns with **DA-001**. |

**Agent mapping:** **Demand** (mill/export/consume context) and **Global** (`agents/global_signals/`) — supply/demand/inventory (**TDS-004 §4.4, §4.6**; TDS-001).

**REQ traceability:** REQ-070, REQ-055, REQ-053, REQ-075.

---

### 3.6 ICAC (International Cotton Advisory Committee)

| Dimension | Assessment |
|-----------|------------|
| **Availability** | **Yes** — authoritative global cotton statistics (production, consumption, trade, stocks, area, yield). |
| **Access method** | **World Cotton Database** (G10-hosted, **registration + Terms of Use**; use limited to management/analysis of ICAC cotton statistics—no public REST API) ([icac.gen10.net](https://icac.gen10.net/)); **ICAC Open Data Dashboard** (Shiny) supports compile-and-download workflows ([open data dashboard](https://icac.shinyapps.io/ICAC_Open_Data_Dashboaard)); publications e.g. Cotton This Month ([Cotton This Month](https://icac.org/publications/cotton-this-month)). Secretariat contact: statistician@icac.org. |
| **Refresh frequency** | **Monthly** (Cotton This Month) with periodic revisions to datasets—aligns with slower global agent cadence. |
| **Historical depth** | **1920/21–present** in World Cotton Database; **1940s+** in core ICAC sets. |
| **Licensing concerns** | **World Cotton Database** G10 end-user terms restrict use to ICAC cotton statistics management/analysis; website terms prohibit sell/rent/sublicense/redistribute ICAC material without permission ([ICAC terms](https://icac.org/home/terms-and-conditions)). Commercial KrishiNetra embedding requires **written Secretariat approval**—not assumed from free dashboard access. |
| **Confidence** | **Medium–High** — Strong domain fit for **Global** and **Demand** agents. Downgraded vs USDA on **automation clarity** (API/export contract for nightly ingest). |

**Agent mapping:** **Global** (`agents/global_signals/`) and **Demand** — global inventories, trade, consumption (**DATA_DOMAINS DD-006, DD-004**; cotton §12 global inventories).

**REQ traceability:** REQ-070, REQ-055, REQ-053.

---

## 4. Cross-Source Comparison (Phase 1 Ingest Priority)

| Source | Agent(s) | Ingest priority | Automation readiness | Blocks cotton MI alone? |
|--------|----------|-----------------|----------------------|-------------------------|
| Agmarknet | Market | P0 | Medium (OGD/API TBD) | No (Futures required per registry) |
| eNAM | Market | P2 | Low | No |
| IMD | Weather | P1 | Medium (API + whitelist) | No (optional agent) |
| NCDEX | Futures | P0 (via commercial) | Low until licensed | **Yes** if no REQ-071 feed |
| USDA | Demand, Global | P1 | High | No |
| ICAC | Demand, Global | P1 | Medium | No |

---

## 5. Assumption Validation (founder)

| Assumption | Verdict | Notes |
|------------|---------|-------|
| **DA-001** Public sources usable | **Partially confirmed** | USDA/ICAC/Agmarknet/IMD viable with access work; eNAM automation weak |
| **DA-002** Commercial futures obtainable | **Plausible, uncontracted** | NCDEX/MCX paths exist; **DS-001** remains blocker |
| **DA-003** Agmarknet lag/gaps | **Confirmed risk** | Mitigation via FD-030 still required |
| **DA-008** Daily refresh adequate | **Confirmed** for Phase 1 | Except futures may need EOD minimum |

---

## 6. E-03 Ingest Implications (non-code)

1. **Registry strings (E-02-S04):** Keep source names exactly as Agmarknet, eNAM, IMD, USDA, ICAC; map NCDEX only under commercial `futures_feed` metadata, not REQ-070 public list.
2. **DataQualitySnapshot:** Plan `agmarknet_lag_hours`, `futures_feed_ok` (TDS-006/TDS-011) from day one.
3. **Basis pipeline (F-03-06):** Requires licensed futures + Agmarknet spot concurrently.
4. **Global agent path:** Persist observations with `source` tags consumed by `agents/global_signals/` per ADR-005.

---

## 7. References (external)

- Agmarknet portal: https://www.agmarknet.gov.in/home  
- OGD Agmarknet mandi prices: https://www.data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi  
- OGD Agmarknet Data API: https://data.gov.in/resources/current-daily-price-various-commodities-various-markets-mandi/api  
- eNAM live prices: https://enam.gov.in/web/dashboard/live_price  
- IMD API reference: https://api.imd.gov.in/public/api_reference.html  
- IMD DSP: https://dsp.imdpune.gov.in/  
- NCDEX data feed: https://ncdex.com/index.php/data-feed/ncdex-authorized-data-feed-vendors  
- USDA FAS data: https://www.fas.usda.gov/data/databases-applications  
- PSD Online: https://apps.fas.usda.gov/psdonline/app/index.html#/app/home  
- ICAC portals: https://icac.org/portals  
- ICAC World Cotton Database: https://icac.gen10.net/  
- ICAC Open Data Dashboard: https://icac.shinyapps.io/ICAC_Open_Data_Dashboaard  
- FAS Open Data Services: https://apps.fas.usda.gov/opendataweb/home  

---

## 8. Document Control

| Field | Value |
|-------|-------|
| Author | Track C (KDO parallel) |
| Status | Complete — Phase 1 validation |
| Next review | After futures vendor selection or DMI API confirmation |
