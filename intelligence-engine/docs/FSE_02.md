# FSE-02 — Data Sources & Collection Pipeline

Canonical programme specification:

[`docs/FSE_02_DATA_SOURCES_COLLECTION_PIPELINE.md`](../../docs/FSE_02_DATA_SOURCES_COLLECTION_PIPELINE.md)

Package: `intelligence-engine/financial_statements_engine/collection/`

Depends on FSE-01 Raw Evidence Layer. Collectors emit Evidence Event Bus events; they do not parse or publish warehouse statements.
