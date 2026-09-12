# FSE-01 — Financial Statements Engine

Canonical financial warehouse for AGIB.

**Spec:** [`docs/FSE_01_FINANCIAL_STATEMENTS_ENGINE.md`](../../docs/FSE_01_FINANCIAL_STATEMENTS_ENGINE.md)

## What this is

Institutional financial data platform — acquire, validate, normalize, version, and publish statements.

**Not** a scraper script, AI summarizer, or BUY/SELL engine.

## Architecture

```text
Official Sources → Collection (FSE-02) → Raw Evidence → Evidence Event Bus
  → Extraction → Normalization → Canonical → Validation → Version Control
  → Warehouse → Derived → Consumers
```

P2.1 `earnings_intelligence` is the NSE XBRL **extraction adapter** during migration.
New consumers must read through FSE — not bypass to parsers.

Specs: [FSE-01](../../docs/FSE_01_FINANCIAL_STATEMENTS_ENGINE.md) · [FSE-02](../../docs/FSE_02_DATA_SOURCES_COLLECTION_PIPELINE.md) · [FSE-03](../../docs/FSE_03_CANONICAL_FINANCIAL_DATA_MODEL.md) · [FSE-04](../../docs/FSE_04_PARSING_NORMALIZATION_ENGINE.md) · [FSE-04.1](../../docs/FSE_04_1_PARSE_MANIFEST_REPLAY_CERTIFICATION.md) · [FSE-04.2](../../docs/FSE_04_2_EVIDENCE_COVERAGE_MATRIX.md) · [FSE-04.3](../../docs/FSE_04_3_PRODUCTION_CERTIFICATION_CORPUS.md) · [FSE-05](../../docs/FSE_05_VALIDATION_FINANCIAL_QUALITY_ENGINE.md) · [FSE-06](../../docs/FSE_06_FINANCIAL_WAREHOUSE.md)

## CLI

```bash
export PYTHONPATH=.
python -m financial_statements_engine --health
python -m financial_statements_engine --dashboard
python -m financial_statements_engine --registry
python -m financial_statements_engine --collection-health
python -m financial_statements_engine --cfdm-health
python -m financial_statements_engine --metric-registry
python -m financial_statements_engine --resolve-metric "Revenue From Operations"
python -m financial_statements_engine --parsing-health
python -m financial_statements_engine --quality-health
python -m financial_statements_engine --certify
python -m financial_statements_engine --benchmark
python -m financial_statements_engine --coverage-health
python -m financial_statements_engine --coverage-dashboard
python -m financial_statements_engine --coverage-analytics
python -m financial_statements_engine --pcc-health
python -m financial_statements_engine --pcc-dashboard
python -m financial_statements_engine --pcc-certify
python -m financial_statements_engine --validation-health
python -m financial_statements_engine --validation-dashboard
python -m financial_statements_engine --validate-ticker TCS
python -m financial_statements_engine --warehouse-health
python -m financial_statements_engine --warehouse-latest TCS
python -m financial_statements_engine --warehouse-contract dcf.v1 TCS
python -m financial_statements_engine --schema-evolution-health
python -m financial_statements_engine --parse-bytes TCS --format json --file ./sample.json --period-end 2025-03-31
python -m financial_statements_engine --collect TCS --mode live
python -m financial_statements_engine TCS
python -m financial_statements_engine TCS --publish
# FSE-FDO Phase 1 — Financial Data Operations (coverage / gaps / ops)
python -m financial_statements_engine --fdo-dashboard
python -m financial_statements_engine --fdo-coverage gold
python -m financial_statements_engine --coverage-company TCS
python -m financial_statements_engine --fdo-schedule
python -m financial_statements_engine --source-health
python -m financial_statements_engine --fdo-alerts
```

## APIs

- `GET /v1/financial-statements/health`
- `GET /v1/financial-statements/dashboard`
- `GET /v1/financial-statements/{ticker}`
- `POST /v1/financial-statements/ingest`
- `GET /v1/financial-statements/cfdm/health`
- `GET /v1/financial-statements/metrics`
- `GET /v1/financial-statements/metrics/resolve?name=`
- `GET /v1/financial-statements/metrics/{metric}`
- `GET /v1/financial-statements/parsing/health`
- `GET /v1/financial-statements/parsing/dashboard`
- `POST /v1/financial-statements/parsing/run`
- `GET /v1/financial-statements/parsing/quality/health`
- `GET /v1/financial-statements/parsing/quality/dashboard`
- `GET /v1/financial-statements/parsing/manifests/{ticker}`
- `GET /v1/financial-statements/parsing/unknown-metrics`
- `POST /v1/financial-statements/parsing/replay`
- `POST /v1/financial-statements/parsing/certify`
- `POST /v1/financial-statements/parsing/benchmark`
- `GET /v1/financial-statements/parsing/coverage/health`
- `GET /v1/financial-statements/parsing/coverage/dashboard`
- `GET /v1/financial-statements/parsing/coverage/analytics`
- `GET /v1/financial-statements/parsing/coverage/matrices/{ticker}`
- `GET /v1/financial-statements/parsing/coverage/matrices/{ticker}/{matrix_id}`
- `GET /v1/financial-statements/parsing/coverage/history/{ticker}`
- `POST /v1/financial-statements/parsing/coverage/diff`
- `GET /v1/financial-statements/parsing/pcc/health`
- `GET /v1/financial-statements/parsing/pcc/dashboard`
- `GET /v1/financial-statements/parsing/pcc/analytics`
- `GET /v1/financial-statements/parsing/pcc/cases`
- `GET /v1/financial-statements/parsing/pcc/history`
- `GET /v1/financial-statements/parsing/pcc/certifications/{id}`
- `POST /v1/financial-statements/parsing/pcc/certify`
- `GET /v1/financial-statements/validation/health`
- `GET /v1/financial-statements/validation/dashboard`
- `GET /v1/financial-statements/validation/reports`
- `POST /v1/financial-statements/validation/run`
- `GET /v1/financial-statements/warehouse/health`
- `GET /v1/financial-statements/warehouse/dashboard`
- `GET /v1/financial-statements/warehouse/latest/{ticker}`
- `GET /v1/financial-statements/warehouse/contracts`
- `GET /v1/financial-statements/warehouse/contracts/{contract_id}/{ticker}`
- `GET /v1/financial-statements/warehouse/view/{ticker}/{view}`
- `GET /v1/financial-statements/schema-evolution/health`
- `GET /v1/financial-statements/schema-evolution/resolve`
- `GET /v1/financial-statements/collection/health`
- `GET /v1/financial-statements/collection/dashboard`
- `GET /v1/financial-statements/collection/ingest-dashboard` (FSE-02.1)
- `GET /v1/financial-statements/collection/source-coverage` (FSE-02.3)
- `GET /v1/financial-statements/collection/source-registry` (FSE-02.3)
- `GET /v1/financial-statements/collection/events`
- `POST /v1/financial-statements/collection/run`
- `POST /v1/financial-statements/collection/run-official` (FSE-02.3)
- `GET /v1/financial-statements/verification/dashboard` (FSE-02.2)
- `GET /v1/financial-statements/verification/workflows`
- `GET /v1/financial-statements/verification/workflows/{workflow_id}`
- `GET /v1/financial-statements/verification/provenance/{workflow_id}`
- `POST /v1/financial-statements/verification/run/{company}`
- `GET /v1/financial-statements/fdo/dashboard` (FSE-FDO)
- `GET /v1/financial-statements/fdo/schedule`
- `GET /v1/financial-statements/fdo/alerts`
- `GET /v1/financial-statements/coverage`
- `GET /v1/financial-statements/coverage/{company}`
- `GET /v1/financial-statements/source-health`

## Frozen surfaces

Constitution · Governance Spec · Decision Engine formulas · Gate thresholds · Evaluation Lab · IAT · Mission Control contracts
