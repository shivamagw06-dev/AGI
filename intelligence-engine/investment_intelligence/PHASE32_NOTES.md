# Phase 3.2 — Investment Intelligence Engine

**Status:** Build complete · Acceptance = 100% · Ask/KUL wired in **Phase 3.2.5**  
**Depends on:** AGI Core v1.1 (extend only) + Business Intelligence + Industry DNA  
**Version:** `3.2.0`

## Discipline

```
Build → Acceptance Test → Integration → Production Validation → Freeze
```

Engine acceptance is green. See `PHASE32_05_NOTES.md` for KUL integration.

## Objective

Answer **"So what?"** for investors — quality, attractiveness, risks, scenarios, valuation drivers, evidence, uncertainty — **without** BUY/SELL recommendations.

## Modules shipped

| Module | Role |
|--------|------|
| Investment Thesis | Structured thesis (quality, position, risks, catalysts, unknowns) |
| Catalyst Intelligence | Positive/negative catalysts with probability, horizon, impact |
| Risk Intelligence | Typed risks with severity, mitigants, leading indicators |
| Scenario Intelligence | Bull / base / bear — **no price targets** |
| Quality Engine | 10-dimension scorecard with why / helped / hurt / unknowns |
| Valuation Intelligence | Consumes Industry DNA methods; sensitivity — no targets |
| Capital Allocation | Organic, dividends, buybacks, M&A, debt, capex evaluation |
| Evidence Confidence | High/medium/low/unknown + missing data |
| Committee Simulation | 9 roles + chair synthesis — NO BUY / NO SELL |
| Investment Graph | Canonical investment object |

## REST

- `GET /v1/investment-intelligence/health`
- `GET /v1/investment-intelligence/dashboard`
- `POST /v1/investment-intelligence/analyse`

## Acceptance

```bash
cd intelligence-engine
python3 ask_product_test/run_investment_intelligence_acceptance_v1.py
```

300 questions · gate **100%** · artifact `investment_intelligence_acceptance_v1.json`

## Explicit non-goals (engine PR)

- No BUY/SELL / price targets
- No Core modifications

## Integration (Phase 3.2.5)

See `PHASE32_05_NOTES.md` — KUL provider, Integration Acceptance (75), Founder V4 (100).
