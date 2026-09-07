# RQ1 Sprint 6 — Intelligence Layer Router (ILR) V1

**Primary question:** What intelligence pipeline should execute?

**Law:** No intelligence layer runs automatically. Execute only the minimum set required for institutional quality.

ILR builds an execution graph with dependencies, parallel groups, suppressions, cost estimates, confidence plans, and **expected contribution scores** (for later ILM learning).

## API

| Method | Path |
|---|---|
| GET | `/v1/layer-router/health` |
| GET | `/v1/layer-router/constitution` |
| GET | `/v1/layer-router/dashboard` |
| GET | `/v1/layer-router/quality-gates` |
| POST | `/v1/layer-router/plan` |
| POST | `/v1/layer-router/diagnostics` |

## Admin

`/admin/layer-router`
