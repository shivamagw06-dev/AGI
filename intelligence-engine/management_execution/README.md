# FIRE-05 — Management Execution & Temporal Evidence Engine

Tracks whether management delivered on prior disclosures using later financial evidence.

**Spec:** [`docs/FIRE_05_MANAGEMENT_EXECUTION_TEMPORAL_ENGINE.md`](../../docs/FIRE_05_MANAGEMENT_EXECUTION_TEMPORAL_ENGINE.md)

## Rules

- Consumes FIRE-03 facts, FIRE-04 (soft), Warehouse/DME, FKB
- Normalizes statements into durable `objective_id` records
- Statuses: Delivered / Partially Delivered / Not Yet Delivered / Cannot Yet Evaluate / Superseded
- Never honesty judgments, fraud detection, legal conclusions, BUY/SELL, or LLM

## CLI

```bash
export PYTHONPATH=.
python -m management_execution --health
python -m management_execution --company TCS
python -m management_execution --timeline TCS
python -m management_execution --score TCS
python -m management_execution --objectives TCS
```

## API

- `GET /v1/management-execution/health`
- `GET /v1/management-execution/dashboard`
- `GET /v1/management-execution/company/{ticker}`
- `GET /v1/management-execution/company/{ticker}/timeline`
- `GET /v1/management-execution/company/{ticker}/score`
- `GET /v1/management-execution/company/{ticker}/objectives`
