# AGI v4.0 Phase 5 Sprint 5.3 — Institutional Portfolio Office (IPO)

```text
COMPANY: AGI
RELEASE: AGI v4.0 Institutional Investment Office
MODULE: IPO
VERSION: institutional-portfolio-office-v1.0.0
SCHEMA: ipo-idea-schema-v1.0.0
```

## Philosophy

Portfolio management is **relative**, not absolute.

```text
Companies → Relative Ranking → Portfolio Office (ideas)
```

Stores **Portfolio Ideas**, never positions.

## Layering

| Object | Question |
|--------|----------|
| Investment Thesis | Why is this interesting? |
| Investment Decision | What governance action? |
| **Portfolio Idea** | How does this compare with everything else? |
| Position (later) | Has capital been allocated? |

## PortfolioIdea fields

company · sector · theme · investment_thesis · decision · relative_rank ·
conviction · expected_role · correlation · risk_budget · capacity ·
dependencies · monitoring · status · version

## Roles

Core Compounder · Defensive · Cyclical · Turnaround · Event Driven ·
Income · Macro Hedge · Cash Alternative · Satellite

## Policies

Max single-name ideas · sector concentration · theme capacity ·  
`allow_positions=false` · `allow_execution=false`

## APIs

`/v1/portfolio/{health,dashboard,telemetry,history,create,list,ranking,:id,:id/versions}`

## Measurement

**PQS** — Portfolio Quality Score (independent of CIO / prior metrics).

## LangSmith

`portfolio_office` after `decision_office`.
