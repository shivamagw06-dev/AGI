# Institutional Scenario Intelligence (ISI) — Sprint 9.2

Evaluates **Bull / Base / Bear** scenarios from IFI Forecast Bundles.

Judgment-first: plausible outcomes for the Investment Office — not a single prediction.

## Primary question

**What are the plausible outcomes?**

## Rules

- No BUY / SELL / target prices  
- No probabilities (deferred to PCI 9.4)  
- Contradictions preserved  
- Evidence required on every scenario  

## APIs

- `GET /v1/scenarios/company/{ticker}`
- `GET /v1/scenarios/sector/{sector}`
- `GET /v1/scenarios/market`
- `GET /v1/scenarios/macro`
- `POST /v1/scenarios/report`
- `GET /v1/scenarios/dashboard`

## Tests

```bash
cd intelligence-engine
python -m pytest institutional_scenario_intelligence/tests -q
```
