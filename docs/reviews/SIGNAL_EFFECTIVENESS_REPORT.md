# Signal Effectiveness Report — PI10 Track E

**Date:** 2026-06-04
**PI:** PI10 Track E (KDO — statistical correlation vs forward cotton prices)
**Method:** Pearson + Spearman correlation; **no ML**
**Data source:** `synthetic_fixture_panel (5433 corpus insufficient)`

---

## 1. Verdict

| Question | Answer |
|----------|--------|
| Analysis window | `2023-06-01` → `2026-06-03` |
| Evaluable days (panel) | **1099** |
| Validated price rows loaded | **4836** |
| Arrival rows loaded | **4836** |
| Weather rows loaded | **6045** |
| Primary markets | **4** TG basket |
| Best signal @ 30d (|r|) | **price_momentum** @ 30d — Pearson **+0.1526**, Spearman **+0.1679**, n=**1099** |
| Weakest signal @ 30d (|r|) | **rainfall_shock** @ 30d — Pearson **+0.0060**, Spearman **+0.0025**, n=**1099** |

Forward target: **basket modal** percent change from validated `price_observation` (median of primary-market modal medians). Horizons: **7d**, **30d**.

---

## 2. Sample sizes

| Metric | Count |
|--------|-------|
| Evaluable calendar days | **1099** |
| `price_momentum` non-null signal days | **1099** |
| `arrival_momentum` non-null signal days | **1099** |
| `rainfall_shock` non-null signal days | **1099** |
| `temperature_stress` non-null signal days | **1099** |
| Forward return `7d` non-null | **1099** |
| Forward return `30d` non-null | **1099** |

---

## 3. Correlation matrix

| Signal | Horizon | n | Pearson r | Spearman ρ | Mean signal | Mean fwd return |
|--------|---------|---|-----------|------------|-------------|-----------------|
| `price_momentum` | 7d | **1099** | +0.3620 | +0.3545 | +0.5253 | +0.0023 |
| `price_momentum` | 30d | **1099** | +0.1526 | +0.1679 | +0.5253 | +0.0096 |
| `arrival_momentum` | 7d | **1099** | +0.0461 | +0.0252 | +0.0090 | +0.0023 |
| `arrival_momentum` | 30d | **1099** | +0.0487 | +0.0429 | +0.0090 | +0.0096 |
| `rainfall_shock` | 7d | **1099** | -0.0004 | -0.0082 | +0.2432 | +0.0023 |
| `rainfall_shock` | 30d | **1099** | +0.0060 | +0.0025 | +0.2432 | +0.0096 |
| `temperature_stress` | 7d | **1099** | +0.0023 | +0.0040 | +0.3815 | +0.0023 |
| `temperature_stress` | 30d | **1099** | -0.0101 | -0.0097 | +0.3815 | +0.0096 |

---

## 4. Interpretation notes

- **Price momentum** — z-score of basket modal vs 30d rolling window; expect positive correlation with forward returns in trending regimes.
- **Arrival momentum** — z-score of basket arrivals (Oct–Mar gate); supply-side invert; weak correlation is common in sparse arrival panels.
- **Rainfall shock** — |today − prior 7d mean| / max(prior mean, 5 mm); [0, 1] weather spike feature.
- **Temperature stress** — |T_mean − 28°C| / 10°C; [0, 1] heat/cold stress.

Ranking uses **|Pearson r|** at the **30d** horizon unless sample size forces fallback to 7d pairs.

---

## 5. Deliverables

| Artifact | Path |
|----------|------|
| Analysis module | `backend/app/services/research/signal_effectiveness/` |
| CLI | `scripts/signal_effectiveness_analysis.py` |
| Unit tests | `tests/unit/test_signal_effectiveness.py` |
| Synthetic panel | `backend/app/services/research/signal_effectiveness/synthetic_panel.py` |

---

## 6. Reproduce

```bash
DATABASE_URL=postgresql://krishinetra:krishinetra@127.0.0.1:5433/krishinetra \
  uv run python scripts/signal_effectiveness_analysis.py --write-report

uv run pytest tests/unit/test_signal_effectiveness.py -q
```

---

## 7. Metrics payload

```json
{
  "data_source": "synthetic_fixture_panel (5433 corpus insufficient)",
  "window_start": "2023-06-01",
  "window_end": "2026-06-03",
  "primary_market_count": 4,
  "price_observation_count": 4836,
  "arrival_observation_count": 4836,
  "weather_observation_count": 6045,
  "panel_summary": {
    "evaluable_days": 1099,
    "price_momentum": 1099,
    "arrival_momentum": 1099,
    "rainfall_shock": 1099,
    "temperature_stress": 1099,
    "forward_7d": 1099,
    "forward_30d": 1099,
    "date_min": "2023-06-01",
    "date_max": "2026-06-03"
  },
  "ranking_horizon_days": 30,
  "best_signal": {
    "signal": "price_momentum",
    "horizon_days": 30,
    "pearson_r": 0.15263137948121508,
    "spearman_rho": 0.1678921372280859,
    "sample_size": 1099,
    "mean_signal": 0.5253120109190172,
    "mean_forward_return": 0.009648371249024325
  },
  "worst_signal": {
    "signal": "rainfall_shock",
    "horizon_days": 30,
    "pearson_r": 0.005970415565510245,
    "spearman_rho": 0.002477849237117397,
    "sample_size": 1099,
    "mean_signal": 0.2432144676979072,
    "mean_forward_return": 0.009648371249024325
  },
  "correlations": [
    {
      "signal": "price_momentum",
      "horizon_days": 7,
      "pearson_r": 0.3619993540079997,
      "spearman_rho": 0.35450262402106836,
      "sample_size": 1099,
      "mean_signal": 0.5253120109190172,
      "mean_forward_return": 0.0022651435838948004
    },
    {
      "signal": "price_momentum",
      "horizon_days": 30,
      "pearson_r": 0.15263137948121508,
      "spearman_rho": 0.1678921372280859,
      "sample_size": 1099,
      "mean_signal": 0.5253120109190172,
      "mean_forward_return": 0.009648371249024325
    },
    {
      "signal": "arrival_momentum",
      "horizon_days": 7,
      "pearson_r": 0.046092576259193004,
      "spearman_rho": 0.025242003494253325,
      "sample_size": 1099,
      "mean_signal": 0.009031119199272065,
      "mean_forward_return": 0.0022651435838948004
    },
    {
      "signal": "arrival_momentum",
      "horizon_days": 30,
      "pearson_r": 0.04873769084657472,
      "spearman_rho": 0.04288651088543022,
      "sample_size": 1099,
      "mean_signal": 0.009031119199272065,
      "mean_forward_return": 0.009648371249024325
    },
    {
      "signal": "rainfall_shock",
      "horizon_days": 7,
      "pearson_r": -0.0003797366586799919,
      "spearman_rho": -0.008210255302662626,
      "sample_size": 1099,
      "mean_signal": 0.2432144676979072,
      "mean_forward_return": 0.0022651435838948004
    },
    {
      "signal": "rainfall_shock",
      "horizon_days": 30,
      "pearson_r": 0.005970415565510245,
      "spearman_rho": 0.002477849237117397,
      "sample_size": 1099,
      "mean_signal": 0.2432144676979072,
      "mean_forward_return": 0.009648371249024325
    },
    {
      "signal": "temperature_stress",
      "horizon_days": 7,
      "pearson_r": 0.0022816804100554903,
      "spearman_rho": 0.0039889318426551005,
      "sample_size": 1099,
      "mean_signal": 0.38149135577798,
      "mean_forward_return": 0.0022651435838948004
    },
    {
      "signal": "temperature_stress",
      "horizon_days": 30,
      "pearson_r": -0.010125277341340815,
      "spearman_rho": -0.00972865675185478,
      "sample_size": 1099,
      "mean_signal": 0.38149135577798,
      "mean_forward_return": 0.009648371249024325
    }
  ]
}
```

*End of signal effectiveness report — PI10 Track E.*
