# Portfolio Intelligence Office (PIO) V1

Primary question: **Does this company improve this specific portfolio?**

Soft institutional layer between Investment Committee and CIO. Never issues buy/sell instructions. Never replaces company analysis.

Includes **Portfolio Quality Engine (PQE)** — portfolio-level Business / Financial / Management / Accounting / Capital Allocation / Valuation Discipline / Evidence / Knowledge scores (soft-consumes MII + ACI).

## Pipeline

```text
… → Institutional Analysts → Investment Committee → PIO → CIO → Research Writer → …
```

## Flag

`PORTFOLIO_INTELLIGENCE=true`

## APIs

- `GET /v1/portfolio-intelligence/portfolio/{id}`
- `GET /v1/portfolio-intelligence/health/{id}`
- `GET /v1/portfolio-intelligence/scenarios/{id}`
- `POST /v1/portfolio-intelligence/analyse`
- `GET /v1/admin/portfolio-intelligence`
