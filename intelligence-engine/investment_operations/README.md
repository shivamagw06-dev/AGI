# P5 — Investment Operations Layer (IOL)

Orchestration layer that turns AGIB’s existing intelligence engines into continuous institutional workflows.

**Not an intelligence engine.** Does not reason, does not bypass CID, does not modify Decision Engine governance, does not issue BUY/SELL.

## Capabilities

| Module | Purpose |
|---|---|
| Morning Office | Daily analyst briefing |
| Research Queue | Prioritised work queue |
| Portfolio Operations | Holdings impact / review (no allocation) |
| Monitoring Office | Meaningful change watches |
| Decision Replay | Reconstruct memory→delta→graph→OIE→CID→DE inputs |
| Daily Brief | Morning / midday / closing / weekend / monthly |
| Catalyst Calendar | Aggregated catalysts linked to CompanyMemory |
| Alert Centre | Explainable institutional alerts |
| Workspace | Unified company page |
| Operational Metrics | Platform health |

## APIs

```
GET /v1/investment-operations/health
GET /v1/investment-operations/morning-office
GET /v1/investment-operations/research-queue
GET /v1/investment-operations/portfolio
GET /v1/investment-operations/alerts
GET /v1/investment-operations/catalysts
GET /v1/investment-operations/workspace/{ticker}
GET /v1/investment-operations/decision-replay/{ticker}
GET /v1/investment-operations/daily-brief
GET /v1/investment-operations/metrics
```

## CLI

```bash
python -m investment_operations --morning
python -m investment_operations --ic10
python -m investment_operations TCS
```
