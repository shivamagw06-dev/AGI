# RQ1 Sprint 5 — Institutional Analyst Router (IAR) V1

**Primary question:** Which institutional specialists are required to answer this question?

**Law:** Institutional research is not democracy. Only relevant specialists participate; suppressed analysts must not execute.

IAR extends the Research Objective Engine. It is **not** a top-level intelligence layer.

## Output

```json
{
  "required_analysts": [],
  "optional_analysts": [],
  "suppressed_analysts": [],
  "speaking_order": [],
  "weights": {},
  "dependencies": {},
  "assignments": [],
  "routing_confidence": {}
}
```

Each participating analyst receives a **Research Assignment** (mandate, questions to answer, success criteria, max length) before any execution.

## API

| Method | Path |
|---|---|
| GET | `/v1/analyst-router/health` |
| GET | `/v1/analyst-router/constitution` |
| GET | `/v1/analyst-router/dashboard` |
| GET | `/v1/analyst-router/quality-gates` |
| POST | `/v1/analyst-router/route` |
| POST | `/v1/analyst-router/diagnostics` |

## Admin

`/admin/analyst-router`
