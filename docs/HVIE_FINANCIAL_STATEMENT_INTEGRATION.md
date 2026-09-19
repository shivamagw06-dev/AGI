# Phase 8.3B — HVIE Financial Statement Integration

**Version:** 8.3B  
**Admin:** `/admin/hvie-runtime`  
**APIs:** `/v1/hvie/{company,history,statistics,percentiles,bands,regimes,rerating,coverage}/{symbol}`  
(also available under `/v1/historical-valuation/*`)

## Principle

HVIE **never downloads vendor historical PE / PB / EV**.

HVIE reconstructs them from warehouse tables only:

```text
Upstox / Yahoo / NSE  →  Warehouse (UIFI)  →  HVIE
```

| Warehouse input | Role |
|---|---|
| `daily_market_history` | Prices |
| `financials_annual` | Income / Balance / Cash Flow |
| `financials_quarterly` | Same, for TTM |
| `corporate_actions` | Dividends + structural actions |
| `valuation_ratios` | Current ratios for validation only — never history |

## Reconstruction v2.0

For each observation date:

1. Take the historical price  
2. Select the latest **published** statement (filing date / lag)  
3. Prefer **CONSOLIDATED** over STANDALONE (never mix in one series)  
4. Prefer **quarterly TTM** → annual → skip  
5. Apply corporate actions / share count  
6. Write point-in-time multiples to `historical_valuation`

### Metrics written

- Historical PE, PB  
- Enterprise Value, EV/EBITDA, EV/Sales, Price/Sales  
- Dividend yield  
- Point-in-time ROE, ROCE, ROA  

### DQIV

Reject / null a multiple when denominator is missing, zero, or negative (e.g. loss-making PE left null). VPAE still gates read paths (banks hide EV/EBITDA, etc.).

## Waiting states (admin board)

| Lifecycle | Meaning |
|---|---|
| `WAITING_PRICE_HISTORY` | Need daily prices |
| `WAITING_STATEMENTS` | Need annual or quarterly financials |
| `WAITING_SHARE_COUNT` | Need `shares_outstanding` for P/B and EV |
| `WAITING_CORPORATE_ACTIONS` | Reserved |
| `READY` / `COMPLETE` | Eligible / finished |

## Success targets

| Metric | Target |
|---|---|
| Vendor historical ratio downloads | **0** |
| Warehouse-only reconstruction | **100%** |
| Eligible names with percentiles / regimes | >95% |
| Daily append success | >99% |

## Consumers

UVE, VARIE, RIE, FIE, Portfolio Office, Investment Office, Ask AI — none recalculate historical valuation; they read HVIE outputs.
