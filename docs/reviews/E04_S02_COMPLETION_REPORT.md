# E-04-S02 Completion Report — Weather Signal Runtime

**Date:** 2026-06-04  
**Story:** E-04-S02 — Weather Signal Runtime (PI9 Track B)  
**Workspace:** `e9fa355` + Track C `0012`  
**Input:** Validated (or received if validated unavailable) `weather_observation` for 5 TG regions  
**Specification:** [SIGNAL_ENGINE_V1.md](../research/SIGNAL_ENGINE_V1.md) §4, [WEATHER_DATA_STRATEGY_V1.md](../research/WEATHER_DATA_STRATEGY_V1.md)

---

## 1. Summary

| Question | Answer |
|----------|--------|
| Weather signal generator implemented? | **Yes** — `WeatherSignalGenerator` |
| Deterministic / replayable? | **Yes** — fixed formulas, `Decimal` quantization, no LLM/forecast |
| Four sub-signals emitted? | **Yes** — `rainfall_deviation`, `rainfall_shock`, `temperature_stress`, `harvest_risk_indicator` |
| Persisted via signal repos? | **Yes** — `StructuredSignalRepository.insert_signal` |
| Unit tests | **11** (`tests/unit/test_weather_signal_generator.py`) |

**Overall:** **PASS** — PI9 Track B deliverable ready for SignalSnapshot assembly (Track C) and replay harness (Track D).

---

## 2. Generator

| Item | Path |
|------|------|
| Entry point | `backend/app/services/signals/weather/generator.py` |
| Feature math | `backend/app/services/signals/weather/features.py` |
| Observation loader | `backend/app/services/signals/weather/observations.py` |
| Constants | `backend/app/services/signals/weather/constants.py` |
| Shared helpers | `backend/app/services/signals/common.py` |

### 2.1 Inputs

| Input | Source | Selection rule |
|-------|--------|----------------|
| Regional daily weather | `weather_observation` | 5 TG `region_id`s from `DISTRICT_REGION_IDS` |
| Validation | `validation_status` | Prefer **validated** → published → received |
| Source filter | NASA POWER default | `source=nasa_power` (IMD-ready when licensed) |
| Lookback | 365 days | Climatology + 30d windows |

### 2.2 Four deterministic features (`signal_components`)

| Feature | Range | Definition |
|---------|-------|------------|
| `rainfall_deviation` | [-1, 1] | 30d mean vs prior 30d norm; regional equal-weight rollup |
| `rainfall_shock` | [0, 1] | \|today − prior 7d mean\| / max(prior mean, 5 mm) |
| `temperature_stress` | [0, 1] | \|T_mean − 28°C\| / 10°C |
| `harvest_risk_indicator` | [0, 1] | 0.6×(7d rain / 80 mm) + 0.4×humidity excess; harvest/storage calendar gate |

Composite **direction**, **magnitude**, **confidence**, and **value** follow SIGNAL_ENGINE_V1 §4.3–§4.6 (`primary_driver` threshold 0.15; lifecycle stage weights H/M/L).

### 2.3 Output

| Field | Rule |
|-------|------|
| `agent_type` | `Weather` |
| `signal_components` | Four features + `primary_driver`, coverage metadata |
| `source_observation_refs` | Observation UUIDs in lookback window |
| `agent_version` | `weather_signal_v1.0.0` |

**Out of scope (per story):** forecast rain, decision rules, LLM text.

---

## 3. Persistence

| Method | Repository |
|--------|------------|
| `WeatherSignalGenerator.persist` | `StructuredSignalRepository.insert_signal` |
| `WeatherSignalGenerator.generate_and_persist` | Compute + append-only insert |

Append-only and magnitude/confidence ∈ [0, 1] enforced at repository layer (E-01-S05 / PI9 Track C).

---

## 4. Verification

| Check | Result |
|-------|--------|
| `uv run ruff check .` | **Pass** |
| `uv run mypy backend/app` | **Pass** |
| `uv run pytest tests/unit/test_weather_signal_generator.py -m 'not integration'` | **10 passed** |
| `uv run pytest tests/unit/test_weather_signal_generator.py` (with DB) | **11 passed** (1 integration) |

---

## 5. Deliverables

| Artifact | Path |
|----------|------|
| Weather signal generator | `backend/app/services/signals/weather/generator.py` |
| Unit tests | `tests/unit/test_weather_signal_generator.py` |
| **This report** | `docs/reviews/E04_S02_COMPLETION_REPORT.md` |

---

## 6. Follow-up

1. Promote `weather_observation` rows to **validated** via Track F batch for production confidence labels.
2. Wire `WeatherSignalGenerator` into daily refresh orchestration (E-04-S08 — out of PI9 stop rule).
3. Extend replay harness (Track D) with weather generator hash cycles.

---

*End of E-04-S02 completion report.*
