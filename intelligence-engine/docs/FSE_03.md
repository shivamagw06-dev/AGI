# FSE-03 — Canonical Financial Data Model & Schema

Canonical programme specification:

[`docs/FSE_03_CANONICAL_FINANCIAL_DATA_MODEL.md`](../../docs/FSE_03_CANONICAL_FINANCIAL_DATA_MODEL.md)

Packages:

* `intelligence-engine/financial_statements_engine/cfdm/` — CFDM objects
* `intelligence-engine/financial_statements_engine/metric_registry/` — versioned Metric Registry service

No downstream system may define its own financial schema. All naming goes through the Metric Registry.
