# YFP V1 Validation — Yahoo Finance Institutional Provider

## Architecture

```
Yahoo Finance → YahooFinanceProvider → Canonical Mapper → MarketDataClient
  → LEO evidence / CID soft-merge → Ask AGI
```

- Priority **40** (secondary after IndianAPI 10 / Finnhub 20 / FMP 30)
- Feature flags: `YAHOO_PROVIDER`, `YAHOO_PROFILE`, `YAHOO_FINANCIALS`, …
- **No Yahoo-native payloads** leave the adapter

## Verified

| Check | Result |
|---|---|
| Registered in Provider Registry | Yes |
| Canonical quote via chart | Live: INFY / HDFCBANK |
| OHLCV / splits / dividends | Mapped from chart events |
| Fundamentals quoteSummary | Mapped (crumb when available) |
| Fundamentals fallback | Chart meta → company name, 52w, price |
| CID soft-merge | Fills empties only; never overwrites |
| LEO source `yahoo` | Selected for market/valuation evidence |
| Admin `/admin/yahoo-provider` | Health, flags, search, enrich probe |
| API `/v1/yfp/*` | health, dashboard, search, enrich, quality-gates |
| Tests | `tests/test_yfp_v1.py` |

## Success criteria

- [x] Integrated through Provider Registry  
- [x] Canonical models only  
- [x] CID automatically enriched (soft)  
- [x] Ask AGI benefits via CID / LEO  
- [x] No architecture deviations  
- [x] Production-ready with graceful crumb fallback  
