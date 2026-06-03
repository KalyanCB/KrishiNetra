# Track D — Forecast Implementation Research

**Program:** KrishiNetra KDO Parallel Execution  
**Track owner:** Track D worker  
**Last updated:** 2026-06-03

---

## Status

| Field | Value |
|-------|-------|
| **Phase** | Research design complete |
| **Branch** | `feature/forecast-research` — **not created** (git repository unavailable in workspace) |
| **Deliverable** | [`docs/research/FORECAST_RESEARCH_DESIGN.md`](../research/FORECAST_RESEARCH_DESIGN.md) |
| **Model selection** | **None** — comparison only per TDS-007 §6.2 |
| **Blocking upstream** | E-03 observations, E-04 signals, futures feed contract (DS-001) for full bake-off |

---

## Completed

- [x] Derived target variables, horizons, and feature map from TDS-007 §5–6
- [x] Defined validation methodology (walk-forward, 12mo promotion holdout, regime/seasonality, leakage, REQ-103 replay)
- [x] Defined calibration methodology per TDS-011 §5 (deterministic `calibration_version`)
- [x] Defined DVA benchmark methodology and promotion gates per TDS-000 §6 and TDS-011 §9
- [x] Compared LightGBM, XGBoost, Prophet, Ensemble — pros/cons, data needs, determinism/replay (REQ-103)
- [x] Explicit no-winner statement and founder-gate traceability
- [x] Updated PROGRAM_STATUS.md Track D section only

---

## In Progress

_None — Track D research scope stopped at design doc per charter._

---

## Next (Handoff to E-06 / Program)

- [ ] Initialize git branch `feature/forecast-research` when repo is available
- [ ] Implement F-06-02 candidate runners with pinned `model_version` strings
- [ ] Run F-06-03 bake-off using scorecard in FORECAST_RESEARCH_DESIGN §10
- [ ] Founder approval for published `is_published` model (TDS-007 §15)

---

## Open Questions

| ID | Question | Severity |
|----|----------|----------|
| TDS-007 | Final model selection after offline bake-off | High — founder approval |
| DS-001 | Futures feed vendor contract | High — blocks credible curve benchmark |
| TDS-000 | PROPOSED RMSE/MAPE targets | Medium — monitoring only |
| OQ-007 | Outcome capture UX | Medium — live calibration (E-10) |
| OQ-009 | Legal promotion gate | Medium |
| — | Expanding vs rolling 24mo train window | Low — protocol detail |
| — | Price level vs log-return training target | Low — publish consistency |

---

## Traceability

| Artifact | Link |
|----------|------|
| Research design | [FORECAST_RESEARCH_DESIGN.md](../research/FORECAST_RESEARCH_DESIGN.md) |
| Forecast architecture | [TDS-007](../tds/TDS-007-Forecast-Architecture.md) |
| Calibration | [TDS-011](../tds/TDS-011-Calibration-Architecture.md) |
| KPI / DVA gates | [TDS-000](../tds/TDS-000-KPI-Framework.md) |
| Epic mapping | [TDS-014](../tds/TDS-014-Epic-Mapping.md) § E-06 |

---

## Risks

| Risk | Mitigation in design |
|------|----------------------|
| Ensemble replay failure | Version entire blend DAG; 30-date REQ-103 audit mandatory |
| Agmarknet gaps | LightGBM/XGB missing-value handling + DataQuality penalties |
| DVA-negative but low RMSE | Explicit reject rule (FD-009) in §5.5 |
| Promotion without futures | Gate G6 + DS-001 resolution before production claims |
