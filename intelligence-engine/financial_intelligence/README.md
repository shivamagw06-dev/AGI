# FIRE-01 — Financial Narrative & Trend Engine

Evidence-backed financial intelligence over the Financial Warehouse.

**Spec:** [`docs/FIRE_01_FINANCIAL_NARRATIVE_TREND_ENGINE.md`](../../docs/FIRE_01_FINANCIAL_NARRATIVE_TREND_ENGINE.md)

## Rules

- Reads Warehouse + DME + validation + coverage only
- Never mutates financial facts
- Never BUY / SELL / target / forecast / DCF
- No LLM-generated opinions — templated narratives only

## CLI

```bash
export PYTHONPATH=.
python -m financial_intelligence --health
python -m financial_intelligence --financial-intelligence TCS
python -m financial_intelligence --financial-findings TCS
python -m financial_intelligence --financial-drivers TCS
python -m financial_intelligence --financial-relationships TCS
```

## API

- `GET /v1/financial-intelligence/health`
- `GET /v1/financial-intelligence/dashboard`
- `GET /v1/financial-intelligence/company/{ticker}`
- `GET /v1/financial-intelligence/findings/{ticker}`
- `GET /v1/financial-intelligence/company/{ticker}/drivers` (FIRE-02)
- `GET /v1/financial-intelligence/company/{ticker}/relationships` (FIRE-02)
