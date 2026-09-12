# FIRE-06 — Business Quality Engine

Deterministic synthesis of FIRE-01…05 evidence into pillar-primary business quality scores.

**Spec:** [`docs/FIRE_06_BUSINESS_QUALITY_ENGINE.md`](../../docs/FIRE_06_BUSINESS_QUALITY_ENGINE.md)

## Rules

- Pillar scores are primary; overall score is derived from FKB-loaded weights
- Management Execution reuses FIRE-05 (no duplicated logic)
- Never BUY/SELL/valuation/DCF/recommendations/LLM
- Never invent evidence

## CLI

```bash
export PYTHONPATH=.
python -m business_quality --health
python -m business_quality --company TCS
python -m business_quality --quality TCS
python -m business_quality --pillars TCS
```

## API

- `GET /v1/business-quality/health`
- `GET /v1/business-quality/dashboard`
- `GET /v1/business-quality/company/{ticker}`
- `GET /v1/business-quality/company/{ticker}/quality`
- `GET /v1/business-quality/company/{ticker}/pillars`
