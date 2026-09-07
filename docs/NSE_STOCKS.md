# NSE all-equity research / trading universe

AGIB ships the official NSE cash equity book as the set of **equities available for trading**.

| File | Count (approx.) | Role |
|------|------------------|------|
| `EQUITY_L.csv` | ~2,390 | Raw NSE securities list (source upload) |
| `NIFTYstocks.csv` | ~2,360 | Normalized EQ/BE/SM trading universe |
| `Nifty500.csv` | 500 | Index constituents (industry labels + tiering) |

Industry labels for the Nifty 500 overlap are copied from `Nifty500.csv`; other names are tagged `NSE Equity`.

## Refresh

From the live NSE archive:

```bash
python3 server/scripts/refresh_nifty_stocks.py
```

From a local upload (e.g. dashboard export):

```bash
python3 server/scripts/refresh_nifty_stocks.py --in /path/to/EQUITY_L.csv
```

This writes both `EQUITY_L.csv` (raw) and `NIFTYstocks.csv` (normalized).

## Intelligence engine

Module: `intelligence-engine/trading_universe/`

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/v1/trading-universe/health` | Count + series mix |
| GET | `/v1/trading-universe/dashboard` | Summary + sample |
| GET | `/v1/trading-universe/symbols` | Full symbol list |
| GET | `/v1/trading-universe/search?q=` | Name/ticker search |
| GET | `/v1/trading-universe/symbol/{symbol}` | Single membership |

Node BFF mirrors under `/api/intelligence/trading-universe/*`.

`production_hardening` preset `all` / `nse` / `equity_l` loads this book. Historical-depth `supported_universe()` includes NSE-listed names beyond Nifty 500.

## Analyse / publish

Requires `GROWW_ACCESS_TOKEN` (or key+secret) and Supabase service-role credentials in `server/.env`:

```bash
cd server
python3 scripts/nifty500_research_engine.py --once
```

The worker auto-selects `NIFTYstocks.csv` when present. See `server/scripts/README-nifty500-research.md`.
