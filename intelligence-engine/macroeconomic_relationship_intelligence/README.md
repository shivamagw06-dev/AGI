# Macroeconomic Relationship Intelligence (MRI) — Sprint 10.3

Evidence-backed macro relationship graph — the macro twin of company HRI.

## Principle

Relationships are never inferred without supporting historical evidence. Versioned, traceable, store-only retrieval.

## Pipeline

```text
HMIP + Historical Company/Sector/Market Knowledge
  → Discovery → Validation → Macro Relationship Graph → Gateway → Forecast IE
```

## APIs

```text
GET  /v1/macro/relationships
GET  /v1/macro/relationships/{indicator}
GET  /v1/macro/relationships/company/{ticker}
GET  /v1/macro/relationships/sector/{sector}
GET  /v1/macro/relationships/graph
POST /v1/macro/relationships/run
GET  /v1/mri/health
GET  /v1/admin/macro-relationships
```

## Traces

`macro_relationship_discovery` · `macro_relationship_validation` · `macro_relationship_graph` · `macro_relationship_retrieval`
