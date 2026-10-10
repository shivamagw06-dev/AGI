# Forecast Validation & Learning (FVL) — Sprint 9.5

Closes the Phase 9 Forecast Intelligence Platform loop.

> **Were we right?**

## Position

```text
IFI → ISI → CTI → IPCI → Forecast Registry → FVL → Learning → ILO / Knowledge Platform
```

## Guarantees

- Forecasts are **registered and versioned** before validation
- Validation records are **immutable** and traceable
- Historical forecast snapshots are **never rewritten**
- Learning creates **new** process-memory objects
- No live Yahoo / NSE calls; no BUY/SELL / target prices

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
```

## Traces

`forecast_validation` · `forecast_scoring` · `forecast_learning` · `forecast_calibration`

## Status lifecycle

```text
Pending → Monitoring → Validated | Partially Correct | Incorrect | Indeterminate
```
