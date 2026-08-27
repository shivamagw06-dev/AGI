# Institutional Forecast Intelligence (IFI) — Sprint 9.1

Assembles **Forecast Bundles** from AGI-owned knowledge only.

Not a price prediction engine. Does not choose Bull/Base/Bear or assign probabilities.

## Primary question

**What evidence-backed context should inform forward-looking institutional scenarios?**

## APIs

- `GET /v1/forecast/company/{ticker}` (default `mode=bundle`)
- `GET /v1/forecast/sector/{sector}`
- `GET /v1/forecast/market`
- `GET /v1/forecast/macro`
- `GET /v1/forecast/theme`
- `POST /v1/forecast/bundle`
- `GET /v1/forecast/dashboard`
- `GET /v1/ifi/*` aliases

## Tests

```bash
cd intelligence-engine
python -m pytest institutional_forecast_intelligence/tests -q
```
