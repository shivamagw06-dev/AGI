# Phase 3.3 — Portfolio Intelligence Engine

**Status:** Build complete · Acceptance target 100% · Ask/KUL **not wired**  
**Depends on:** AGI Core v1.1 (extend only) + Investment Intelligence 3.2 + Industry DNA  
**Version:** `3.3.0`  
**Package:** `portfolio_intelligence/foundation/` (coexists with legacy PIO soft layer)

## Discipline

```
Build → Acceptance Test → Integration → Production Validation → Freeze
```

This PR stops after **Acceptance = 100%**. Modules 12–17 (KUL, Integration Acceptance, Founder V5, freeze) are deferred.

## Objective

Answer **"How does this company fit within an entire portfolio?"** — construction, diversification, exposures, risk budget, correlation, quality, attribution, scenarios, monitoring — **without** BUY/SELL or trade recommendations.

## Modules shipped

| Module | Role |
|--------|------|
| Portfolio Object | Canonical holdings → cash → allocations → style/factor → risk → objectives → constraints |
| Construction Engine | Diversification, concentration, conviction, sizing, trade-offs |
| Exposure Intelligence | Sector, industry, FX, rates, commodity, style, factors |
| Risk Budget Engine | Position/sector/factor/liquidity/correlation/tail/drawdown with severity, drivers, mitigants |
| Correlation Intelligence | Positive/low relationships, diversification benefit, hidden concentration |
| Quality Engine | Portfolio quality beyond weighted averages (consumes INV profiles) |
| Performance Attribution | Allocation / selection / currency / macro framing |
| Rebalancing Intelligence | Drift explanation only — **no trade recommendations** |
| Scenario Engine | Bull/base/bear + shocks (rates, commodity, FX, recession, recovery, regulatory, tech) |
| Monitoring Intelligence | Portfolio Monitoring Object |
| Knowledge Graph | Holdings → industries → macro → factors → currencies → risks → catalysts → correlations |
| Executive Brief | Summary → diversification → key risks → sector exposures → monitoring → evidence → unknowns |

## REST

- `GET /v1/portfolio-intelligence/foundation/health`
- `GET /v1/portfolio-intelligence/foundation/dashboard`
- `GET /v1/portfolio-intelligence/foundation/portfolios`
- `POST /v1/portfolio-intelligence/foundation/analyse`
- `POST /v1/portfolio-intelligence/foundation/soft_slice` (blocked while `ASK_WIRED=False`)

Legacy PIO routes under `/v1/portfolio-intelligence/*` remain unchanged.

## Acceptance

```bash
cd intelligence-engine
PYTHONPATH=. python3 ask_product_test/run_portfolio_intelligence_acceptance_v1.py
```

300 questions · gate **100%** · artifact `portfolio_intelligence_acceptance_v1.json`

## Explicit non-goals (this PR)

- No KUL provider registration
- No Ask wiring (`ASK_WIRED = False`)
- No BUY/SELL / trade recommendations / price targets
- No Core modifications
- No replacement of legacy PIO soft APIs

## Next

1. Register `portfolio_intelligence` in KUL  
2. Portfolio Integration Acceptance (~75)  
3. Founder Evaluation V5  
4. Production validation → Freeze Phase 3.3
