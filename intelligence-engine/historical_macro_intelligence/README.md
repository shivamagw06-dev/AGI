# Historical Macroeconomic Intelligence Platform (HMIP) — Sprint 10.2

Immutable historical macro memory — the long-term twin of CMKP (10.1).

## Principle

Historical macro knowledge is never overwritten. Analysis answers regime / cycle questions from the store — never from live APIs.

## Pipeline

```text
Official Historical Sources → Collect → Validate → Normalize → HMKO → Timeline → Store → Gateway → IE
```

## APIs

```text
GET  /v1/macro/history
GET  /v1/macro/history/{indicator}
GET  /v1/macro/history/country/{country}
GET  /v1/macro/history/timeline
GET  /v1/macro/history/search
POST /v1/macro/history/run
GET  /v1/hmip/health
GET  /v1/admin/historical-macro
```

## Traces

`historical_macro_collection` · `historical_macro_validation` · `historical_macro_normalization` · `historical_macro_publication` · `historical_macro_retrieval`
