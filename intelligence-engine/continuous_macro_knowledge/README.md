# Continuous Macroeconomic Knowledge Platform (CMKP) — Sprint 10.1

Standalone continuous macro ingestion — independent of Ask, Research and Forecast.

## Principle

> Macroeconomic intelligence should behave exactly like company intelligence. Official macro releases continuously update AGI's institutional knowledge. User requests consume published macro knowledge—they never trigger data collection.

## Pipeline

```text
Official Sources → Collect → Validate → Normalize → Materiality → Learn → Publish → Store → Gateway → IE
```

## Sources

India: RBI, MOSPI, NSO, MoF, CGA, SEBI  
Global: FRED, IMF, World Bank, OECD

## APIs

```text
GET  /v1/macro/india
GET  /v1/macro/global
GET  /v1/macro/dashboard
GET  /v1/macro/indicator/{indicator}
GET  /v1/macro/releases
GET  /v1/macro/calendar
POST /v1/macro/run          # ops/scheduler only
GET  /v1/cmkp/health
GET  /v1/admin/macro-operations
```

## Traces

`macro_collection` · `macro_validation` · `macro_normalization` · `macro_materiality` · `macro_learning` · `macro_publication`
