# P4.5 — Opportunity Intelligence Engine (OIE)

Institutional research prioritisation — answers:

> Where should institutional research effort be focused today, and why?

**Does not** issue BUY/SELL, target prices, or portfolio actions. Decision Engine governance unchanged.

## Consumes (compiled intelligence only)

- CompanyMemory / Knowledge Delta Engine
- Investment Knowledge Graph
- Institutional Scenario Intelligence
- Hypothesis Engine
- Confidence Calibration

Never queries raw market APIs.

## Outputs

Opportunity Pack with score, research priority (`Critical|High|Medium|Low|Monitor`), Why Now, strengths, blockers, catalysts, dimension contributions, explainability.

## APIs

- `GET /v1/opportunity-intelligence/health`
- `GET /v1/opportunity-intelligence/{ticker}`
- `GET /v1/opportunity-intelligence/top`
- `GET /v1/opportunity-intelligence/watchlist`
- `GET /v1/opportunity-intelligence/catalysts`
- `GET /v1/opportunity-intelligence/research-priority`

## CLI

```bash
python -m opportunity_intelligence TCS
python -m opportunity_intelligence --ic10
python -m opportunity_intelligence --watchlist
```
