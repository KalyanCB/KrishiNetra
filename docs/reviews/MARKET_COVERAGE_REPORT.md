# Market Coverage Report — PI7 Track B

**Date:** 2026-06-04  
**PI:** PI7 Track B (KDO — cotton registry market expansion)  
**Seed:** `backend/app/persistence/seeds/fixtures/cotton.json`  
**Research basis:** [AGMARKNET_PRODUCTION_ONBOARDING.md](../research/AGMARKNET_PRODUCTION_ONBOARDING.md), [COTTON_DOMAIN_MODEL_V1.md](../research/COTTON_DOMAIN_MODEL_V1.md), [E02_SEED_PREPARATION_PLAN.md](../implementation/E02_SEED_PREPARATION_PLAN.md)

---

## 1. Summary

| Metric | Value |
|--------|-------|
| **Agmarknet cotton markets seeded** | **27** |
| Prior baseline (Telangana only) | 4 |
| States covered | 5 (Telangana, Maharashtra, Gujarat, Andhra Pradesh, Karnataka) |
| Lookup tests | `tests/unit/test_cotton_market_coverage.py` |
| Backfill / runtime signal | **Not run** (Track A deferred) |

Phase 1 cotton belt expansion adds central and western India mandis (Maharashtra, Gujarat) plus adjacent Andhra Pradesh and Karnataka markets, while deepening Telangana coverage beyond the original four proof mandis.

---

## 2. `market_id` and normalization conventions

| Rule | Detail |
|------|--------|
| **Pattern** | `mkt_{state_code}_{location_slug}` — e.g. `mkt_mh_amravati`, `mkt_tg_khammam_apmc` |
| **State codes** | `tg` Telangana, `mh` Maharashtra, `gj` Gujarat, `ap` Andhra Pradesh, `ka` Karnataka |
| **OGD resolution** | `AgmarknetMarketLookup.resolve(state, district, market)` strips whitespace on all three fields |
| **Uniqueness** | One `market_id` per distinct `(state, district, market)` Agmarknet triple |
| **Region FK** | Each market links to a `reg_{state}_{district}` mandi region under `reg_{state}_state` |

**Production note:** Exact `market` spellings follow Agmarknet 2.0 mandi master naming (district-aligned defaults). Re-audit with registered OGD key (`≥20` reporting days in 90-day window per onboarding §6.3) before Track A backfill; update tuples if portal strings differ.

---

## 3. Full Agmarknet market registry (27)

| # | `market_id` | State | District | Market (OGD) | Region |
|---|-------------|-------|----------|--------------|--------|
| 1 | `mkt_tg_khammam_apmc` | Telangana | Khammam | Khammam | `reg_tg_khammam` |
| 2 | `mkt_tg_warangal` | Telangana | Warangal | Warangal | `reg_tg_warangal` |
| 3 | `mkt_tg_karimnagar` | Telangana | Karimnagar | Karimnagar | `reg_tg_karimnagar` |
| 4 | `mkt_tg_kesamudram` | Telangana | Khammam | Kesamudram | `reg_tg_kesamudram` |
| 5 | `mkt_tg_nizamabad` | Telangana | Nizamabad | Nizamabad | `reg_tg_nizamabad` |
| 6 | `mkt_tg_adilabad` | Telangana | Adilabad | Adilabad | `reg_tg_adilabad` |
| 7 | `mkt_tg_nalgonda` | Telangana | Nalgonda | Nalgonda | `reg_tg_nalgonda` |
| 8 | `mkt_tg_jagtial` | Telangana | Jagtial | Jagtial | `reg_tg_jagtial` |
| 9 | `mkt_tg_mancherial` | Telangana | Mancherial | Mancherial | `reg_tg_mancherial` |
| 10 | `mkt_tg_peddapalli` | Telangana | Peddapalli | Peddapalli | `reg_tg_peddapalli` |
| 11 | `mkt_mh_amravati` | Maharashtra | Amravati | Amravati | `reg_mh_amravati` |
| 12 | `mkt_mh_akola` | Maharashtra | Akola | Akola | `reg_mh_akola` |
| 13 | `mkt_mh_yavatmal` | Maharashtra | Yavatmal | Yavatmal | `reg_mh_yavatmal` |
| 14 | `mkt_mh_wardha` | Maharashtra | Wardha | Wardha | `reg_mh_wardha` |
| 15 | `mkt_mh_jalgaon` | Maharashtra | Jalgaon | Jalgaon | `reg_mh_jalgaon` |
| 16 | `mkt_mh_nagpur` | Maharashtra | Nagpur | Nagpur | `reg_mh_nagpur` |
| 17 | `mkt_mh_parbhani` | Maharashtra | Parbhani | Parbhani | `reg_mh_parbhani` |
| 18 | `mkt_mh_latur` | Maharashtra | Latur | Latur | `reg_mh_latur` |
| 19 | `mkt_gj_rajkot` | Gujarat | Rajkot | Rajkot | `reg_gj_rajkot` |
| 20 | `mkt_gj_bhavnagar` | Gujarat | Bhavnagar | Bhavnagar | `reg_gj_bhavnagar` |
| 21 | `mkt_gj_surendranagar` | Gujarat | Surendranagar | Surendranagar | `reg_gj_surendranagar` |
| 22 | `mkt_gj_patan` | Gujarat | Patan | Patan | `reg_gj_patan` |
| 23 | `mkt_ap_guntur` | Andhra Pradesh | Guntur | Guntur | `reg_ap_guntur` |
| 24 | `mkt_ap_adoni` | Andhra Pradesh | Kurnool | Adoni | `reg_ap_adoni` |
| 25 | `mkt_ap_nandyal` | Andhra Pradesh | Kurnool | Nandyal | `reg_ap_nandyal` |
| 26 | `mkt_ka_raichur` | Karnataka | Raichur | Raichur | `reg_ka_raichur` |
| 27 | `mkt_ka_gulbarga` | Karnataka | Gulbarga | Gulbarga | `reg_ka_gulbarga` |

### 3.1 Coverage by state

| State | Markets | Share |
|-------|---------|-------|
| Telangana | 10 | 37% |
| Maharashtra | 8 | 30% |
| Gujarat | 4 | 15% |
| Andhra Pradesh | 3 | 11% |
| Karnataka | 2 | 7% |

---

## 4. Validation performed (Track B)

| Check | Result |
|-------|--------|
| `load_expected_market_ids()` | 27 ids, matches seed Agmarknet entries |
| `AgmarknetMarketLookup` unique keys | PASS |
| All seed tuples resolve to `market_id` | PASS (`test_market_lookup_resolves_all_seed_tuples`) |
| Whitespace normalization | PASS |
| `market_id` regex convention | PASS |
| Seed runner changes | **None required** — generic `markets[]` upsert already handles expansion |
| Integration DB backfill | **Skipped** per scope |

---

## 5. Sample new `market_id` values (non-baseline)

| `market_id` | Agmarknet tuple |
|-------------|-----------------|
| `mkt_tg_nizamabad` | Telangana / Nizamabad / Nizamabad |
| `mkt_mh_yavatmal` | Maharashtra / Yavatmal / Yavatmal |
| `mkt_gj_rajkot` | Gujarat / Rajkot / Rajkot |
| `mkt_ap_guntur` | Andhra Pradesh / Guntur / Guntur |
| `mkt_ka_raichur` | Karnataka / Raichur / Raichur |

---

## 6. Follow-ups (Track A / ops)

1. OGD 90-day audit per market; drop or rename tuples where reporting `<20` days.
2. Run `agmarknet_backfill.py` only after production `api-key` — updates `HISTORICAL_BACKFILL_REPORT.md` coverage stats.
3. Extend `ogd_telangana_sample.json` or add multi-state fixtures for mapper CI when needed.

---

*End of PI7 Track B market coverage report.*
