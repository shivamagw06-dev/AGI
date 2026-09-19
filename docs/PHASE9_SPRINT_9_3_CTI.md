# Phase 9 – Sprint 9.3

# Catalyst & Trigger Intelligence (CTI)

## Mission

Answer the institutional question:

> **What events would make us change our view?**

CTI does **not** forecast. It determines what could invalidate or strengthen the current Bull / Base / Bear view.

```text
We are Base Case unless X happens.
```

## Position in Phase 9

| Sprint | Module | Status |
|---|---|---|
| 9.1 | Institutional Forecast Intelligence | ✅ (FIE forecast bundles) |
| 9.2 | Institutional Scenario Intelligence | ✅ (Bull / Base / Bear scenarios) |
| **9.3** | **Catalyst & Trigger Intelligence** | **➡️ this sprint** |
| 9.4 | Probability & Confidence Intelligence | Next |
| 9.5 | Forecast Validation & Learning | Next |

## Architecture

```text
Institutional Scenario Intelligence
                │
                ▼
Current Bull/Base/Bear
                │
                ▼
Catalyst Intelligence (company / sector / macro / market)
                │
                ▼
Trigger Evaluation Engine
                │
                ▼
Monitoring Office → Investment Office
```

## What shipped

- Package: `intelligence-engine/catalyst_trigger_intelligence/`
- Catalyst catalog + generation from FIE scenarios / knowledge priors
- Full Trigger objects with lifecycle: Scheduled → Watching → Triggered → Confirmed → Applied → Archived
- Scenario impact assessment **without** auto-rewriting theses or governance
- Trigger matrix (Trigger → Effect)
- Monitoring Office soft-wire (review / committee review only)
- LangSmith-oriented traces: `catalyst_generation`, `trigger_monitoring`, `trigger_evaluation`, `scenario_update`
- Mission Control dashboard: `/v1/cti/dashboard`, `/v1/admin/catalyst-trigger-intelligence`

## APIs

```text
GET  /v1/catalysts/company/{ticker}
GET  /v1/catalysts/sector/{sector}
GET  /v1/catalysts/market
GET  /v1/triggers/company/{ticker}
GET  /v1/triggers/report
POST /v1/triggers/evaluate
GET  /v1/cti/health
GET  /v1/cti/dashboard
GET  /v1/cti/monitoring/{ticker}
```

## Success criteria

- AGI identifies company, sector, market and macro catalysts  
- Every catalyst produces deterministic trigger conditions  
- Trigger states tracked through lifecycle  
- Activations update scenario assessments — never auto-rewrite theses  
- Monitoring Office consumes CTI to prioritise reviews  

## Verification

```bash
cd intelligence-engine
PYTHONPATH=. pytest -q catalyst_trigger_intelligence/tests/test_cti.py
```
