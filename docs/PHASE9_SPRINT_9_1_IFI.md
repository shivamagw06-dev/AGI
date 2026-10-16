# Phase 9 — Sprint 9.1: Institutional Forecast Intelligence (IFI)

**Status:** Implemented in `intelligence-engine/institutional_forecast_intelligence/`  
**Version:** 0.1.0  
**Depends on:** Phase 6 knowledge, Phase 8 historical intelligence (soft HIP bridge)  
**Out of scope:** Scenario selection (9.2), catalysts/triggers as judgment (9.3), price prediction

---

## Naming

Not a “Forecast Knowledge Builder.”  
**Institutional Forecast Intelligence (IFI)** — prepares institutional scenarios from evidence, history and current knowledge. It does **not** predict prices.

---

## Objective

Transform AGI-owned knowledge into **Forecast Bundles** that the Scenario Engine can consume without further retrieval.

```text
Live Knowledge + Historical Knowledge + Research
+ Relationships + Analogues + (Pattern when ready)
        │
        ▼
Institutional Forecast Intelligence
        │
        ▼
Forecast Bundle  →  Scenario Engine (9.2)
```

---

## What IFI does **not** do

- Predict stock prices  
- Recommend BUY / SELL  
- Assign probabilities  
- Choose Bull / Base / Bear  
- Optimise portfolios  
- Execute trades  
- Call live Yahoo / NSE / BSE during bundle generation  

---

## APIs

```text
GET  /v1/forecast/company/{ticker}     # default mode=bundle (IFI)
GET  /v1/forecast/sector/{sector}
GET  /v1/forecast/market
GET  /v1/forecast/macro
GET  /v1/forecast/theme
POST /v1/forecast/bundle
GET  /v1/forecast/dashboard
GET  /v1/ifi/*                         # aliases
```

Legacy FIE scenario output: `GET /v1/forecast/company/{ticker}?mode=fie` or `/v1/forecast/scenarios/{ticker}`.

---

## Success path

```bash
curl 'http://127.0.0.1:8000/v1/forecast/company/INFY'
curl -X POST http://127.0.0.1:8000/v1/forecast/bundle \
  -H 'content-type: application/json' \
  -d '{"scope":"company","entity":"INFY"}'
```

Returns a Forecast Bundle with current knowledge, historical intelligence, analogues, relationships, research, monitoring, catalysts, risks, completeness and provenance — `providers_queried: []`.

---

## Completeness

Missing Pattern Intelligence (Sprint 8.5) or HIP enrichment reduces completeness scores. IFI never invents missing sections.

---

## Milestone

| Phase | Capability |
|---|---|
| 6 | Know what is happening |
| 7 | Research what is happening |
| 8 | Remember what happened before |
| **9.1** | **Prepare evidence for what could happen next** |
| 9.2 | Evaluate alternative future scenarios |
