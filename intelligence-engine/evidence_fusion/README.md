# FIRE-04 — Evidence Fusion Engine

Deterministic cross-evidence consistency over FIRE-01/02/03 + warehouse metrics.

**Spec:** [`docs/FIRE_04_EVIDENCE_FUSION_ENGINE.md`](../../docs/FIRE_04_EVIDENCE_FUSION_ENGINE.md)

## Rules

- Consumes Warehouse, DME, FIRE-01 findings, FIRE-02 relationships, FIRE-03 business facts, FKB
- Never mutates upstream data; never reads collectors
- Outcomes: Supported / Partially Supported / Not Supported / Insufficient Evidence
- Never BUY / SELL / valuation / forecast / sentiment / LLM conclusions
- Never judges management honesty or infers intent

## CLI

```bash
export PYTHONPATH=.
python -m evidence_fusion --health
python -m evidence_fusion --company TCS
python -m evidence_fusion --supported TCS
python -m evidence_fusion --conflicts TCS
python -m evidence_fusion --alignment TCS
```

## API

- `GET /v1/evidence-fusion/health`
- `GET /v1/evidence-fusion/dashboard`
- `GET /v1/evidence-fusion/company/{ticker}`
- `GET /v1/evidence-fusion/company/{ticker}/supported`
- `GET /v1/evidence-fusion/company/{ticker}/conflicts`
- `GET /v1/evidence-fusion/company/{ticker}/alignment`
