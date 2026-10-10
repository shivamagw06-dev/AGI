# Phase 2 — AGI Product Experience

## Guiding principle

Users think in **Companies · Portfolios · Research · Markets · Ideas · Ask AGI**.

They never need to know about FIRE modules, Office SDK, PEB, or CIO engine IDs.

## Product navigation

```
AGI
├── Dashboard
├── Ask AGI
├── Companies
├── Portfolio
├── Markets
├── Research
├── Watchlists
├── Screeners
├── Notebook
├── Alerts
└── Settings
```

Entry route: `/agi` (full-bleed product shell; no public Header/Footer).

## Flagship surfaces (Sprint 2.1–2.3)

| Surface | Route | Status |
| ------- | ----- | ------ |
| Dashboard | `/agi` | Shipped — institutional command centre |
| Ask AGI | `/agi/ask` | Shipped — conversational entry (reuses chat workspace) |
| Company Workspace | `/agi/companies/:ticker` | Shipped — wired to CW-01 APIs |

Remaining nav items are product-language placeholders that route back to the three flagships until their sprints land.

## Design language

Minimal · light · professional — Bloomberg × Apple × Notion.

Product CSS: `src/pages/agi/agi.css`  
Shell: `src/pages/agi/AgiLayout.jsx`

## Continuous workflow

Dashboard → Ask AGI → Company → Evidence → Research Note → Portfolio → Decision → Monitor

## Backend contract

Company Workspace UI consumes:

- `GET /company-workspace/{ticker}`
- `GET /company-workspace/{ticker}/timeline`
- `GET /company-workspace/{ticker}/evidence`

Presentation only — no BUY/SELL, no analysis runs from the UI.

## Roadmap

| Sprint | Deliverable | Priority |
| ------ | ----------- | -------- |
| 2.1 | Dashboard | ★★★★★ |
| 2.2 | Ask AGI UI | ★★★★★ |
| 2.3 | Company Workspace UI | ★★★★★ |
| 2.4 | Research Workspace | ★★★★ |
| 2.5 | Portfolio Workspace | ★★★★ |
| 2.6 | Markets Dashboard | ★★★★ |
| 2.7 | Screeners | ★★★ |
| 2.8 | Watchlists | ★★★ |
| 2.9 | Notebook | ★★★★ |
| 2.10 | Alerts Centre | ★★★ |
