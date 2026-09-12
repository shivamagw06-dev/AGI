# LEO v1.0 Validation

## Mission

Close the External API Audit gap: vendor / corporate evidence must reach **Used in reasoning** on Ask AGI / CAE / IRP — without building a new engine.

## HDFC Bank (`Should I buy HDFC Bank?`)

| Check | Result |
|---|---|
| LEO enabled | Yes |
| Evidence objects | 54+ |
| External sources used | `nse`, `bse`, `company_ir`, `rbi` (+ internal_research) |
| Vendor keys attempted | groww, indianapi, finnhub, twelve_data, fmp, fred, alphavantage (empty/unconfigured in this env) |
| Documents / announcements | Annual, quarterly, presentations, transcripts, NSE/BSE announcements |
| Macro | RBI streams |
| Sector framework | banks (SIF) |
| Finance Academy | concepts attached |
| Influenced reasoning | **Yes** (`live_evidence.influenced_reasoning`) |
| Recommendation | Withheld — SIF + LEO must-have gate (market_data / statements / valuation still missing without live vendor keys) |

## Multi-ticker quality gates

HDFCBANK, INFY, RELIANCE, ULTRACEMCO, POWERGRID, SUNPHARMA, TATASTEEL — each produces evidence objects with external contribution.

## Status shift vs External API Audit

| Source class | Before LEO | After LEO |
|---|---|---|
| NSE / BSE / Company IR / RBI (AOI) | Configured / not on Ask AGI | **Used in reasoning** |
| Groww / IndianAPI / Finnhub / FMP / FRED / … | Called on market routes only | **Called by LEO when selected**; contribute when keys + Node reachable |
| Ask AGI path | Academy + SIF only | LEO → EVE → CAE → Academy → SIF → IRP |

## Completion criteria

- [x] External / corporate sources contribute to production reasoning
- [x] Company documents gathered, normalised, verified (soft EVE), packaged
- [x] Announcements update living company dossiers
- [x] Finance answers expose LEO evidence plan + provenance
- [x] API usage measurable (`/v1/leo/dashboard`, `/admin/live-evidence`)
- [x] No new reasoning engine; architecture v1.0.1 locked
