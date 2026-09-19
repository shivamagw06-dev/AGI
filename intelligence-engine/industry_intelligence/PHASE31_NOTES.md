# Phase 3.1 — Industry Intelligence Engine

**Status:** Build complete · Acceptance = 100% · Ask/KUL wired in Phase 3.1.5  
**Depends on:** AGI Core v1.0 (extend only — do not modify Core)  
**Version:** `3.1.0`  
**Integration:** see `PHASE31_05_NOTES.md`

## Discipline

```
Build → Acceptance Test → Integration → Production Validation → Freeze
```

This PR stops after **Acceptance = 100%**. Module 14 (Ask/KUL provider registration) is intentionally deferred.

## What shipped

Package: `intelligence-engine/industry_intelligence/`

| Module | Role |
|--------|------|
| Industry Registry | 36 first-class industries + aliases |
| Industry DNA | Canonical object (economics, KPIs, valuation, regulation, competition, cycle, risks, graph) |
| KPI Engine | Deterministic industry KPIs with definition / ranges / relationships |
| Economics Engine | Causal why-margins / ROIC / leverage / WC / valuation |
| Cycle Engine | Primary cycle + lifecycle + macro sensitivity |
| Regulation Engine | Regulators + regulatory risks |
| Valuation Engine | Industry-specific methods (never universal) |
| Competition Engine | Structure + Porter forces |
| Risk Engine | Weighted industry risks |
| Industry Graph | Customers / suppliers / adjacent / substitutes / capital allocation |
| Cross-Industry | Deterministic pedagogy answers (P/B, EV/Sales, low airline ROIC, etc.) |

REST (engine-only):

- `GET /v1/industry-intelligence/health`
- `GET /v1/industry-intelligence/dashboard`
- `POST /v1/industry-intelligence/analyse`
- `GET /v1/industry-intelligence/industry/{industry_key}`
- `GET /v1/industry-intelligence/industry/{industry_key}/kpi/{kpi_key}`

Acceptance:

- `ask_product_test/industry_intelligence_acceptance_v1.py` — 200 questions
- Runner: `ask_product_test/run_industry_intelligence_acceptance_v1.py`
- Gate: **100%** before Ask integration

## Industry DNA (canonical)

Every industry exposes a structured DNA object consumed later by Business / Investment / Portfolio Intelligence — not duplicated.

```
Identity · Economics · KPIs · Value/Cost/Margin drivers · Capital intensity
Working capital · Cash conversion · Regulation · Competition · Valuation
Lifecycle · Risks · Macro sensitivity · Graph relationships
```

## Explicit non-goals (engine)

- No Core module edits
- No LLM summaries
- No Ask bypass outside KUL

## Integration

Phase 3.1.5 (`PHASE31_05_NOTES.md`) registers the KUL provider, makes BI consume Industry DNA, and adds Integration Acceptance + Founder V3.
