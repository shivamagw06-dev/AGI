# PRE-01 — Institutional Portfolio Risk Engine

Phase 4.3 — Authoritative portfolio risk for the Investment Office.

## Mission

Company risk already exists. Portfolio decisions already exist.

PRE-01 introduces **institutional portfolio risk** as an independent, versioned object that every higher-level component (CIO-01, scenarios, observations, Investment Committee) consumes.

## Architecture

```text
Holdings
  ↓
Portfolio Graph (PKG-01)
  ↓
Portfolio Risk Engine (PRE-01)
  ↓
InstitutionalPortfolioRisk
  ↓
Portfolio Decision (CIO-01)
  ↓
Investment Office
```

Dependency chain:

```text
Evidence → Knowledge Graph → Company Decision → Portfolio Graph (PKG-01)
  → Portfolio Risk (PRE-01) → Portfolio Decision (CIO-01) → Investment Office
```

* **PKG-01** answers: *What does the portfolio look like?*
* **PRE-01** answers: *What risks does the portfolio have?*
* **CIO-01** answers: *Given those risks and company decisions, what actions should we take?*

## Package

`intelligence-engine/institutional_portfolio_risk/`

## Object

`InstitutionalPortfolioRisk` — immutable, versioned.

Dimensions: concentration, sector/factor/country exposure, liquidity, market beta, correlation proxies, volatility proxies via stress, tail risk via deterministic stress scenarios.

## Engines

| Engine | Role |
|--------|------|
| Concentration | HHI, top positions, sector/theme, Low→Critical |
| Liquidity | ADV / exit-days proxies, portfolio liquidity score |
| Correlation | Phase-1 proxies (sector/industry/macro) + `CorrelationProvider` |
| Factor | Growth/Value/Momentum/Quality/Size + sector/macro tags |
| Stress | Deterministic scenarios (RBI ±50bps, market −10/−20, oil, INR, banking) |

## Out of scope

Monte Carlo, VaR, CVaR, options Greeks, derivative risk, optimisation, real-time market simulation.

## CLI

```bash
PYTHONPATH=intelligence-engine python3 -m institutional_portfolio_risk --portfolio default
```

## API

- `GET /v1/portfolio-risk/health`
- `POST /v1/portfolio-risk`
- `GET /v1/portfolio-risk/{portfolio}`

BFF: `/api/intelligence/portfolio-risk/*`

## Quality gates

Reject if missing holdings, exposures, diagnostics, stress results, or concentration analysis.

## Success criteria

- Portfolio risk is a first-class object
- CIO-01 consumes PRE-01 instead of calculating risk
- Stress / concentration / liquidity deterministic
- Explainable lineage
- Versioned immutable risk objects
