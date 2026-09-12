# Evidence Intelligence Layer (EIL) V1

**Architecture status:** v1.0.1 LOCKED  
**Purpose:** Fix the primary ACS/IRS weakness — evidence quality.

Soft layer only. No engine / analyst / ACS / IRS redesign.

## Rules

1. Never label priors / memory seeds as observed evidence  
2. Never say bare “Street” — name Bloomberg / MS / LSEG / internal  
3. Every Fact claim carries `SourceRef` + optional `MetricPoint`  
4. Confidence is decomposed: Evidence × Historical × Peer × Macro  
5. Peer/history gaps stay visible until populated  
6. Decision triggers: evidence required → timeline → trigger → action  

## Epistemic classes

`fact` · `prior` · `inference` · `judgement` · `street` · `market`

## Live case pack

`live_cases/case_11_jul2026.py` — July 2026 oil + private-bank margin stress (HDFC Q1FY27 filings attributed).

## APIs

- `GET /v1/academy/evidence/health`
- `GET /v1/academy/evidence/dashboard`
- `GET /v1/academy/evidence/case/{case_id}`
- `POST /v1/academy/evidence/support`
- `POST /v1/academy/evidence/confidence`
- `GET /v1/academy/evidence/quality-gates`

## Flag

`evidence_intelligence_layer` / `EVIDENCE_INTELLIGENCE_LAYER`

## Next (not this PR)

Populate full 5y peer panels (ICICI/Kotak/Axis/SBI) from filings automation — do not add more analyst frameworks first.
