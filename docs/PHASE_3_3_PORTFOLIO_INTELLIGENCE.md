# Phase 3.3 — Portfolio Intelligence Engine

Teach AGI to reason about **entire portfolios** — construction, diversification, exposures, risk budgets, correlation, quality, attribution, scenarios, and monitoring — without trade recommendations.

## Status

- **Build:** complete (`portfolio_intelligence/foundation/`)
- **Acceptance:** 300 deterministic questions · gate 100%
- **Ask / KUL:** `ASK_WIRED = False` until acceptance + integration gates
- **Core:** unchanged (extend only)
- **Depends on:** Investment Intelligence 3.2 · Industry Intelligence 3.1 · AGI Core v1.1

## Hierarchy

```
Financial Intelligence
        ↓
Business Intelligence
        ↓
Industry Intelligence
        ↓
Investment Intelligence
        ↓
Portfolio Intelligence   ← Phase 3.3
```

## Package layout

```
intelligence-engine/portfolio_intelligence/foundation/
  schema.py          # PortfolioPackage, ASK_WIRED, policy constants
  catalog.py         # Deterministic sample portfolios
  engines.py         # Construction → monitoring → graph
  orchestrator.py    # Intent detect + executive brief order
  production.py      # Health / dashboard / analyse / soft_slice (blocked)
  PHASE33_NOTES.md
  tests/
```

Legacy PIO soft APIs under `portfolio_intelligence.*` remain untouched.

## REST

| Method | Path |
|--------|------|
| GET | `/v1/portfolio-intelligence/foundation/health` |
| GET | `/v1/portfolio-intelligence/foundation/dashboard` |
| GET | `/v1/portfolio-intelligence/foundation/portfolios` |
| POST | `/v1/portfolio-intelligence/foundation/analyse` |
| POST | `/v1/portfolio-intelligence/foundation/soft_slice` |

## Executive brief order

1. Portfolio Summary  
2. Diversification  
3. Key Risks  
4. Sector Exposures  
5. Monitoring Priorities  
6. Evidence  
7. Unknowns  

## Recommendation policy

`observations_only_no_buy_sell` — no BUY/SELL, no price targets, no trade recommendations (rebalancing explains drift only).

## Acceptance

```bash
cd intelligence-engine
PYTHONPATH=. python3 ask_product_test/run_portfolio_intelligence_acceptance_v1.py
```

## Deferred (same lifecycle as 3.1 / 3.2)

1. KUL provider `portfolio_intelligence`  
2. Portfolio Integration Acceptance (~75 live)  
3. Founder Evaluation V5 (100)  
4. Production regression stack → Freeze  

See also: `docs/KNOWLEDGE_DEPENDENCY_MAP.md`
