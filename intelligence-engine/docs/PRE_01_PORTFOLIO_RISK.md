# PRE-01 — Institutional Portfolio Risk Engine

See root docs: `docs/AGI_PRE_01_PORTFOLIO_RISK.md`.

Package: `intelligence-engine/institutional_portfolio_risk/`

CIO-01 consumes `InstitutionalPortfolioRisk` via `portfolio_risk=` / production façade — it does not recompute concentration or stress when PRE-01 is available.
