# E2E-01 — Institutional Product Experience Validation

## Role

E2E-01 validates the **complete AGI product experience** exactly as a real institutional user would use it.

It is **not**:

- another intelligence engine
- another reasoning benchmark

The Intelligence Core proves AGI can reason.  
IBS proves AGI can reason consistently.  
**E2E-01 proves users can consume that intelligence through a coherent institutional product.**

## Product language

Users think in:

Dashboard · Companies · Research · Portfolio · Markets · Ask AGI · Watchlists

Never in FIRE / Office SDK / PEB / CW / CIO / IO.

## Entry

`/agi`

## Workflows

| ID | Workflow |
| -- | -------- |
| WF1 | Morning Brief (Dashboard) |
| WF2 | Company Research (Kotak) |
| WF3 | Evidence Drill-down |
| WF4 | Ask AGI |
| WF5 | Research |
| WF6 | Portfolio |
| WF7 | Markets |
| WF8 | Watchlists |
| WF9 | Context Awareness |
| WF10 | Navigation |
| WF11 | Performance |
| WF12 | Failure Handling |
| WF13 | Consistency |
| WF14 | Historical Blind (15 May 2024) |
| WF15 | Benchmark (IBS KOTAK_RBI) |

## Scoring

Pass **≥ 90** on a normalized **0–100** scorecard.

| Dimension | Weight |
| --------- | ------ |
| Navigation | 10 |
| Dashboard | 5 |
| Company Workspace | 15 |
| Evidence Drill-down | 10 |
| Ask AGI | 15 |
| Research | 10 |
| Portfolio | 10 |
| Markets | 5 |
| Context Awareness | 10 |
| Performance | 5 |
| Consistency | 5 |
| Failure Handling | 5 |

(Spec weights sum to 105; the runner normalizes to 100.)

## Final question

> Can an experienced institutional investor perform an entire research workflow—from discovering an opportunity to reviewing evidence, understanding portfolio implications, and defining a monitoring plan—using only AGI?

If **YES**, Phase 2 Product Experience is institutionally ready.

## CLI

```bash
cd intelligence-engine
python3 -m product_experience_validation --run
```

## API

- `GET /v1/product-experience/health`
- `GET /v1/product-experience/dashboard`
- `POST /v1/product-experience/run`
- `GET /v1/product-experience/report`
