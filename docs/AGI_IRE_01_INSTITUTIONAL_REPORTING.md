# IRE-01 — Institutional Reporting Engine

Deterministic **Company Recommendation Reports** from structured facts.

**No Gemini. No GPT. No external writer.**

## Workflow

```text
Ask AGI
   │
   ▼
Institutional Report  (Company Recommendation only)
```

## Contract

`InstitutionalReportInput` — immutable facts only (recommendation, conviction, confidence, quality scores, thesis bullets, evidence IDs, …).

`compose_report(input) → InstitutionalReport`

## Fixed sections (never omit)

1. Institutional View  
2. Investment Horizon  
3. Confidence (score + positive / negative / unknowns)  
4. Investment Thesis  
5. Business Quality  
6. Financial Quality  
7. Valuation  
8. Risk Assessment  
9. Bull Case  
10. Bear Case  
11. Watch Items  
12. Evidence  
13. Bottom Line  

## Rules

- Recommendation / conviction / quality contradictions fail validation before render.
- Every paragraph section maps to evidence IDs.
- Quality gates reject incomplete reports.
- Same input → same text (deterministic).

## Access

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_reporting --ticker AXISBANK
PYTHONPATH=. python3 -m institutional_reporting --health
```

API:

- `GET /v1/report/health`
- `POST /v1/report/company` (body = `InstitutionalReportInput` or `{ "ticker": "AXISBANK" }` fixture)
- `GET /v1/report/company/{ticker}`

BFF:

- `GET /api/intelligence/report/health`
- `POST /api/intelligence/report/company`
- `GET /api/intelligence/report/company/:ticker`

## Successor

**IRE-02** adds the Reason Composer (`docs/AGI_IRE_02_REASON_COMPOSER.md`) so every conclusion is backed by structured reasoning before render.

## Out of scope (later sprints)

Market / portfolio / earnings / macro reports, phrase banks, sector language packs, LLM polish.
