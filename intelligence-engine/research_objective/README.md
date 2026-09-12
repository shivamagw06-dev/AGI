# RQ1 Sprint 3 — Research Objective Engine (ROE) V1

**Primary question:** What institutional research objective should drive this workflow?

**Law:** Determine the decision to support before collecting data or executing analysts / intelligence layers.

ROE extends Intent Intelligence. It is **not** a top-level intelligence layer.

## Flow

```
Resolved Question → ROE → Primary Objective + Plan
                         (analysts, layers, APIs, blueprint, confidences)
```

Exactly **one** primary objective. Unlimited secondary objectives. If objective confidence &lt; 85%, stop and clarify.

## API

| Method | Path |
|---|---|
| GET | `/v1/research-objective/health` |
| GET | `/v1/research-objective/constitution` |
| GET | `/v1/research-objective/dashboard` |
| GET | `/v1/research-objective/quality-gates` |
| POST | `/v1/research-objective/plan` |
| POST | `/v1/research-objective/diagnostics` |

## Admin

`/admin/research-planner`

## Success criteria

- Primary objective accuracy ≥ 99%
- Question type / blueprint / analyst / layer routing ≥ 98%
- Average planning &lt; 30 ms
- ≥ 1000 benchmark questions

