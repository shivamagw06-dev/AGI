# Forecast Intelligence Engine (FIE) V1

Institutional scenario & forecast framework. Soft intelligence layer — **not** a price prediction engine.

## Primary question

**What future paths are plausible?** / **What is most likely to happen next?**

## Architecture status

`v1.0.1 LOCKED`

## Position

```
FIL → FDI → MII → ACI → EIL → PIL → CIG → FIE → Analysts → Committee → PIO → CIO → RW → ACS → IRS
```

## Flag

`FORECAST_INTELLIGENCE=true`

## Rules

- Always Bull / Base / Bear / Stress / Recovery
- Measurable triggers only
- Probabilities evidence-backed and dynamic
- Uncertainty explicitly disclosed
- No unsupported price predictions
- No deterministic forecasts

## API

- `GET /v1/forecast/company/{ticker}`
- `POST /v1/forecast/analyse`
- `GET /v1/forecast/scenarios/{ticker}`
- `GET /v1/forecast/catalysts/{ticker}`
- `GET /admin/forecast-intelligence`
