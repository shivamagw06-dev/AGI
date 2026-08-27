# Phase 8.3 — Historical Valuation Intelligence Engine (HVIE)

**Status:** Implemented (+ Continuous Runtime 8.3R)  
**Module:** `intelligence-engine/historical_valuation_intelligence/`  
**Version:** 8.3  
**Depends on:** Warehouse reconstruction + Phase 8.2A VPAE  

Continuous self-maintenance (bootstrap / daily append / weekly stats) is documented in
`docs/HVIE_CONTINUOUS_RUNTIME.md`.

## Philosophy

HVIE **does not download** historical P/E or P/B from vendors.

Every observation is reconstructed from:

- historical market prices (Yahoo / NSE / Upstox)
- historical financial statements (annual + quarterly → TTM)
- corporate actions (dividends; splits via adjusted inputs)
- historical share counts
- Phase 8.2A valuation policy (which metrics may exist)

Observations are append-only, point-in-time, and auditable.

## Architecture

```text
Prices + Statements + Corporate Actions + VPAE + DQIV
        ↓
warehouse backfill valuation_history.reconstruct_company
        ↓
warehouse.historical_valuation  (append-only)
        ↓
HVIE (statistics · bands · percentiles · regimes · rerating)
        ↓
Terminal · Market · Research · Ask · Hedge Fund
```

## Writers

| Function | Role |
|---|---|
| `compute.reconstruct` | Full / ranged reconstruction (wraps warehouse) |
| `compute.incremental_price_update` | Daily append from last cursor |
| `compute.recalculate_from_statement` | Forward-only from release date |

Statement chronology prefers `filing_date` / `effective_date`, else fiscal-label + lag.

## Readers (APIs)

```bash
GET  /v1/historical-valuation/health
GET  /v1/historical-valuation/company/{symbol}?metric=&window=
GET  /v1/historical-valuation/history/{symbol}?metric=&window=
GET  /v1/historical-valuation/statistics/{symbol}?metric=&window=
GET  /v1/historical-valuation/bands/{symbol}
GET  /v1/historical-valuation/percentiles/{symbol}
GET  /v1/historical-valuation/regimes/{symbol}
GET  /v1/historical-valuation/rerating/{symbol}
GET  /v1/historical-valuation/coverage/{symbol}
POST /v1/historical-valuation/reconstruct/{symbol}
```

BFF: `/api/intelligence/historical-valuation/...`  
Admin UI: `/admin/historical-valuation`

## Windows

Always: **1Y · 3Y · 5Y · 10Y · 15Y · 20Y · MAX**  
MAX = listing / available history — never assumed to be 20 years.

Per window: min, max, mean, median, stdev, variance, p25, p75, current percentile, z-score, observation count, span.

## Regimes (own-history percentile)

| Percentile | Regime |
|---|---|
| 0–20 | VERY_CHEAP |
| 20–40 | CHEAP |
| 40–60 | FAIR |
| 60–80 | EXPENSIVE |
| 80–100 | VERY_EXPENSIVE |

## VPAE gate

Banks never get historical EV/EBITDA intelligence. Loss-makers never get historical PE as applicable. ETF/REIT/InvIT policies suppress equity multiples.

## Ask examples

- “Is Infosys expensive?” → current / 10Y median / percentile / regime / coverage  
- “When was TCS cheapest?” → lowest multiple + date  
- “Has HDFC Bank ever traded cheaper?” → percentile prose on primary (P/B)

## Non-goals

- No vendor historical-ratio import  
- No UI-side calculations  
- No buy/sell recommendations  
- Does not replace warehouse reconstruction — HVIE is the intelligence layer over it  

## Tests

```bash
cd intelligence-engine && python3 -m pytest historical_valuation_intelligence/tests/test_hvie.py -q
```
