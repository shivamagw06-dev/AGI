# Phase 3.2.5 — Investment Intelligence Integration

**Status:** KUL wiring complete · Integration Acceptance target ≥90% · Founder V4 ≥95%  
**Depends on:** AGI Core v1.1 + Investment Intelligence Engine (300/300)  
**Ask path:** KUL provider only — no Ask bypass

## What changed

1. Registered `InvestmentIntelligenceProvider` in KUL (`providers/investment_intelligence.py`)
2. Planner menus: investment-shaped → INV → BI → Industry DNA → CapIQ → …
3. Query planner recognizes investment intents (`investment` type + Evaluate/Assess/Analyze + company)
4. Fusion prefers INV summaries for investment-shaped questions
5. Hard provider / dedup exempt / company object investment section
6. `ASK_WIRED = True` via `knowledge_unification.providers.investment_intelligence`
7. Soft slice is diagnostics-only — Ask uses KUL

## Relationship rules

| Layer | Role |
|-------|------|
| Business Intelligence | Company reasoning (model/moat) — never invents scenarios/catalysts/investment quality |
| Industry Intelligence | Industry DNA, valuation frameworks, industry risks/KPIs |
| Financial Intelligence | Financial quality concepts when relevant |
| Investment Intelligence | Investment reasoning — consumes BI + Industry DNA conceptually |

## Acceptance

```bash
cd intelligence-engine
PYTHONPATH=. python3 ask_product_test/run_inv_integration_acceptance_v1.py   # 75 Q, gate ≥90%
PYTHONPATH=. python3 ask_product_test/run_founder_evaluation_v4.py           # 100 Q, gate ≥95%
```

## Explicit non-goals

- No Core modifications
- No parallel Ask router / shortcut
- No BUY/SELL / price targets
- Full production regression stack (Golden Founder 5, Coverage, Reco, …) remains before Freeze GREEN

## Freeze (later)

Investment Freeze Gate turns GREEN only when Integration + Founder V4 + production regression stack all pass.
