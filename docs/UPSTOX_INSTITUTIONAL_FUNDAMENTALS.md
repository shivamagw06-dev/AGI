# Phase 7.4E — Upstox Institutional Fundamentals Integration (UIFI) v1.0

**Status:** Implemented  
**Module:** `intelligence-engine/upstox_fundamentals/`  
**Connector:** `server/providers/upstox.js` + `server/services/upstoxFundamentalsRefresh.js`

## Role

Upstox is AGIB's **primary structured fundamentals provider** for Indian listed companies.

| Source | Role |
|---|---|
| Upstox | Primary structured fundamentals (profile, statements, ownership, peers, key ratios) |
| Capital IQ | Consensus & estimates |
| NSE / LIDI | Primary market disclosures & corporate actions |
| Upstox CA | Secondary validation only |

Products, engines, and Ask **never call Upstox** — they read the Institutional Warehouse.

## Pipeline

```text
Upstox APIs → Node connector → Normalizer → DQIV Gateway → Warehouse → Engines → Products
```

## Datasets

| Dataset | Warehouse | Runtime |
|---|---|---|
| Profile | `company_master` + `profile_history` | Weekly / bootstrap |
| Income / Balance / Cash Flow | `financials_annual` / `financials_quarterly` | Bootstrap + event-driven |
| Shareholding | `ownership` | Bootstrap |
| Competitors | `peer_relationships` | Weekly / bootstrap |
| Corporate actions | `corporate_actions` (confidence 0.55) | Bootstrap / secondary |
| Key ratios | `valuation_ratios` | Daily 18:15 IST (Phase 7.4D) |

Cash flow populates existing financials tabs (CFO/CFI/CFF/capex) — no separate cashflow tables.

## APIs

### Engine (warehouse reads + ingest)

```text
GET  /v1/upstox-fundamentals/health
GET  /v1/upstox-fundamentals/coverage
GET  /v1/upstox-fundamentals/failures
POST /v1/upstox-fundamentals/ingest

GET  /v1/company/profile/{symbol}
GET  /v1/company/profile/history/{symbol}
GET  /v1/company/statements/{symbol}
GET  /v1/company/shareholding/{symbol}
GET  /v1/company/competitors/{symbol}
GET  /v1/company/corporate-actions/{symbol}
```

### Admin / BFF

```text
POST /api/upstox/profile/bootstrap
POST /api/upstox/statements/bootstrap
POST /api/upstox/shareholding/bootstrap
POST /api/upstox/competitors/bootstrap
POST /api/upstox/corporate-actions/bootstrap
POST /api/upstox/bootstrap/start
POST /api/upstox/bootstrap/stop
GET  /api/upstox/bootstrap/status
GET  /api/upstox/coverage
GET  /api/upstox/failures
POST /api/upstox/refresh
```

Admin UI: `/admin/upstox-fundamentals`

## Schedules

| Cadence | Action |
|---|---|
| Daily 18:15 IST | Key ratios (existing) |
| Sunday 08:00 IST | Profile + competitors |
| 1st 11:00 IST | Coverage audit |
| Bootstrap | Resumable queue for all datasets |

## Env

| Flag | Default | Meaning |
|---|---|---|
| `UIFI_SCHEDULER` | true | Weekly/monthly ticks |
| `UIFI_BATCH` | 40 | Refresh batch size |
| `UIFI_BOOTSTRAP_BATCH` | 25 | Bootstrap slice |
| `UIFI_BOOTSTRAP_CONCURRENCY` | 2 | Adaptive concurrency |
