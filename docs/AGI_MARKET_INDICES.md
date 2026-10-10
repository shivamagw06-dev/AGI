# AGI Market Indices — Nifty constituent registry

Index membership for institutional intelligence. Each index CSV lists **stocks that belong to that index**.

## Indices shipped

| Index ID | Display | File | ~Count |
|---|---|---|---:|
| `NIFTY_50` | Nifty 50 | `indices/Nifty50.csv` | 50 |
| `NIFTY_NEXT_50` | Nifty Next 50 | `indices/NiftyNext50.csv` | 50 |
| `NIFTY_100` | Nifty 100 | `indices/Nifty100.csv` | 100 |
| `NIFTY_200` | Nifty 200 | `indices/Nifty200.csv` | 200 |
| `NIFTY_500` | Nifty 500 | `indices/Nifty500.csv` | 500 |
| `NIFTY_MIDCAP_SELECT` | Nifty Midcap Select | `indices/NiftyMidcapSelect.csv` | 25 |
| `NIFTY_BANK` | Nifty Bank | `indices/NiftyBank.csv` | 14 |
| `NIFTY_FINANCIAL_SERVICES` | Nifty Financial Services | `indices/NiftyFinancialServices.csv` | 20 |

Normalized columns: `Company Name,Industry,Symbol,Series,ISIN Code`.

## Refresh

Official NSE Indices:

```bash
python3 server/scripts/refresh_nifty_indices.py
```

From your Market Watch downloads (`MW-NIFTY-*-30-Jul-2026.csv`):

```bash
python3 server/scripts/refresh_nifty_indices.py --mw-dir ~/Downloads
# or one file:
python3 server/scripts/refresh_nifty_indices.py --in ~/Downloads/MW-NIFTY-BANK-30-Jul-2026.csv
```

## Intelligence APIs

| Method | Path |
|---|---|
| GET | `/v1/market-indices/health` |
| GET | `/v1/market-indices/dashboard` |
| GET | `/v1/market-indices` |
| GET | `/v1/market-indices/{index_id}` |
| GET | `/v1/market-indices/{index_id}/symbols` |
| GET | `/v1/market-indices/membership/{symbol}` |

Node BFF: `/api/intelligence/market-indices/*`.

Module: `intelligence-engine/market_indices/`.

## Ask AGI

After deploy, Ask answers index membership factually, for example:

- “Which indices does HDFC Bank come under?”
- “Which stocks are in Nifty Bank?”
- “Is IDBI in Nifty 500?”

Direct answer is built from `indices/*.csv` membership (not invented).
