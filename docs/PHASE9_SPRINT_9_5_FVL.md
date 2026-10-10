# Phase 9 — Sprint 9.5: Forecast Validation & Learning (FVL)

**Status:** Implemented in `intelligence-engine/forecast_validation_learning/`  
**Version:** 0.1.0  
**Depends on:** Sprint 9.4 IPCI Forecast Assessments (ISI/IFI upstream)  
**Completes:** Phase 9 Forecast Intelligence Platform

---

## Objective

Continuously compare AGI’s historical forecasts, scenarios and probability assessments with actual outcomes, measure forecast quality, identify systematic biases, and generate institutional learning for future forecasting.

FVL does **not** rewrite history. It evaluates forecasting performance and creates **new** learning records.

---

## Core question

> **Were we right?**

---

## Architecture

```text
Institutional Forecast Intelligence
            │
            ▼
Scenario Intelligence
            │
            ▼
Probability & Confidence
            │
            ▼
Forecast Registry
            │
            ▼
Forecast Validation Engine
            │
     ┌──────┼─────────┐
     ▼      ▼         ▼
Expected Actual Outcome Difference
     │      │         │
     └──────┼─────────┘
            ▼
Learning Generator
            ▼
Investment Learning Office
            ▼
Knowledge Platform
```

---

## Guarantees

| Rule | Behaviour |
|---|---|
| Registry | Every forecast registered & versioned before validation |
| Immutability | Assessment snapshots never rewritten |
| Validation | Append-only `ForecastValidation` records |
| Learning | New `InvestmentLearning` objects only |
| Providers | No live Yahoo / NSE / BSE on the validation path |
| Trading | No BUY/SELL, target prices, or execution |

---

## Validation status lifecycle

```text
Pending → Monitoring → Validated | Partially Correct | Incorrect | Indeterminate
```

Lifecycle status is a side pointer + append-only log. The registered forecast body stays frozen.

---

## Forecast score

```yaml
Overall / Scenario Accuracy / Probability Calibration /
Catalyst Accuracy / Timing Accuracy / Confidence Calibration
```

---

## APIs

```text
GET  /v1/forecast/validation/{forecast_id}
POST /v1/forecast/validation/{forecast_id}
POST /v1/forecast/register
POST /v1/forecast/validate
GET  /v1/forecast/learning
GET  /v1/forecast/performance
GET  /v1/forecast/calibration
GET  /v1/forecast/history
GET  /v1/forecast/validation/dashboard
GET  /v1/fvl/health
GET  /v1/admin/forecast-validation   # Mission Control HTML
```

---

## LangSmith traces

`forecast_validation` · `forecast_scoring` · `forecast_learning` · `forecast_calibration`

---

## Phase 9 complete

| Sprint | Module | Role |
|---|---|---|
| ✅ 9.1 | IFI | Prepare evidence for forecasting |
| ✅ 9.2 | ISI | Generate Bull / Base / Bear |
| ✅ 9.3 | CTI | Monitor catalysts & triggers |
| ✅ 9.4 | IPCI | Quantify probability & confidence |
| ✅ 9.5 | FVL | Validate vs reality & learn |

Closed-loop Forecast Intelligence Platform — institutional research governance, not automated trading.
