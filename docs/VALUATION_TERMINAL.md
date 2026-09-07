# AGI Institutional Valuation Terminal

**Route:** `/valuation-terminal` (public) · `/admin/valuation-terminal` (admin)
**Engine:** `intelligence-engine/valuation_engine/terminal.py`
**Contract:** Unified Valuation Engine v3.0

## Data path

```
Warehouse
   ↓
Unified Valuation Engine
   ↓
Valuation Terminal
```

The committed Yahoo JSON loader (`market_data/*valuation*.json`) is **retired**.
The terminal never reads snapshot files. Every multiple is computed from warehouse
rows through the engine, with coverage, provenance and a Valuation Health Score.

## What it shows

### Top-down (Sector Valuation Explorer)

1. **All sectors** — live cards under company search (median PE/PB, historical %, opportunity)
2. **Sector workspace** — dashboard, explanation (`sector_lens`), outcome, company table, filters, leaders, distributions, research priorities
3. **Company drill-down** — reuses the existing company valuation pack

See `docs/SECTOR_VALUATION_EXPLORER.md`.

### Company-first (unchanged)

1. **Company search** — autocomplete over `company_master`, recent searches, favorites
2. **Overview** — CMP, market cap, sector, industry, historical/consensus coverage, updated, data quality
3. **Institutional valuation table** — Metric · Company · Industry · Historical · Position · Source
4. **Historical charts** — Price, P/E, P/B, EV/EBITDA, Revenue, EPS, ROE, Div Yield · 1Y–MAX
5. **Sector context** — median, historical median, rank, distribution, peer percentile
6. **Peer comparison** — multiples, ROE, consensus upside, relative score
7. **Valuation explanation** — current → historical → peer → coverage → bottom line
8. **Change log** — why a multiple moved (price declined, EPS unchanged, …)
9. **Coverage / provenance / DQIV** — on every surface
10. **Valuation Health Score** — confidence in the *analysis*, not a buy/sell score

## API

| Route | Purpose |
|---|---|
| `GET /v1/valuation-engine/terminal/health` | Engine + warehouse coverage |
| `GET /v1/valuation-engine/terminal/search?q=` | Company autocomplete |
| `GET /v1/valuation-engine/terminal/company/{symbol}` | Full terminal pack |
| `GET /v1/valuation-engine/terminal/series/{symbol}/{metric}` | Chart series |
| `GET /v1/valuation-engine/terminal/explain/{metric}` | Metric pedagogy |
| `GET /v1/valuation-engine/company/{symbol}` | Engine valuation only |
| `POST /v1/valuation-engine/explain-change` | Attribution between two observations |

Legacy `/v1/valuation-terminal/company/{ticker}` and `/health` now proxy the engine
terminal. `POST /v1/valuation-terminal/ingest` returns `json_loader_retired`.

Mirrored on the Node BFF under `/api/intelligence/valuation-engine/terminal/*`.

## Valuation Health Score

Not investment advice. It answers: *how much confidence should an analyst place
in this valuation view?*

Signals: live price, latest financials, historical depth, consensus, ROE,
conflicts, overrides, metric coverage, DQIV stamp.
