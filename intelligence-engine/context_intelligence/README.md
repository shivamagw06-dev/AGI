# RQ1 Sprint 4 — Context Intelligence Engine (CIE) V1

**Primary question:** What surrounding context is required to answer this correctly?

**Law:** Institutional analysts never analyse a question in isolation.

CIE enriches every request with entity, market, macro, time, portfolio, historical, comparison, event, expectation, scenario and user context — then produces a **Research Context Card** (case file) for all downstream specialists.

## API

| Method | Path |
|---|---|
| GET | `/v1/context-intelligence/health` |
| GET | `/v1/context-intelligence/constitution` |
| GET | `/v1/context-intelligence/dashboard` |
| GET | `/v1/context-intelligence/quality-gates` |
| POST | `/v1/context-intelligence/enrich` |
| POST | `/v1/context-intelligence/diagnostics` |

## Admin

`/admin/context-intelligence`
