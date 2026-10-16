# Upstox Valuation Integration & Institutional Valuation Intelligence v2.0

## Pipeline

```
Upstox Fundamentals (ISIN key-ratios)
        ↓
DQIV gateway
        ↓
warehouse.valuation_ratios  (append-only long format)
        ↓
warehouse.historical_valuation  (daily PE/PB/EV pivot, source=upstox)
        ↓
Unified Valuation Engine
        ↓
Terminal · Market Intelligence · Hedge Fund · Ask
```

No frontend calls Upstox.

## Provider-owned ratios

From `GET /fundamentals/{isin}/key-ratios`:

| Ratio | Stored as |
|-------|-----------|
| P/E | `pe` |
| P/B | `pb` |
| ROA | `roa` |
| ROE | `roe` |
| ROCE | `roce` |
| EV/EBITDA | `ev_ebitda` |

Each row stores **company_value** and **sector_value** (Upstox sector benchmark).

## AGI still computes

Market cap, enterprise value, price/sales, EV/sales, dividend yield, historical median/percentile/rank, relative score, valuation health, research intelligence.

## Engine preference

`valuation_engine.engine.compute` overlays Upstox ratios before derivation. If Upstox supplies PE, CMP÷EPS is **not** used.

## Prerequisite — ISIN on company_master

Upstox fundamentals are **ISIN-keyed**. If `company_master.isin` is null for the universe, key-ratios ingest returns `no_isin_universe` and Sector Intelligence shows Upstox **0%** / Unknown.

Backfill (Upstox NSE EQ instruments → warehouse):

```
POST /api/market/company-isin/backfill
POST /v1/valuation-ratios/isin-backfill
```

Refresh auto-runs this when the ISIN universe is empty.

## Full-universe bootstrap (Phase 7.4d)

One-shot coverage of all ISIN-mapped companies (~30–40 min) lives in a dedicated bootstrap engine — **not** the nightly job.

See [`docs/UPSTOX_BOOTSTRAP.md`](./UPSTOX_BOOTSTRAP.md) and admin UI `/admin/upstox-bootstrap`.

```
POST /api/market/upstox-bootstrap/start
GET  /api/market/upstox-bootstrap/status
```

## Daily schedule (steady-state)

| Time (IST) | Job |
|------------|-----|
| 18:05 | FII/DII institutional flow |
| **18:15** | **Incremental** Upstox key-ratios (~80 names; skips while bootstrap runs) |
| ~18:45 | Warehouse refresh |

Manual batch: `POST /api/market/upstox-valuation-ratios/refresh`

## Why Sector Intelligence looks empty

| Symptom | Cause |
|---------|--------|
| Upstox column 0% | `valuation_ratios` empty — usually no ISINs, or scheduler not yet run |
| Sector / Premium `—` | Honest empty state until Upstox sector_value lands (not peer-median fake) |
| Hist %ile Unknown | Sparse `historical_valuation.percentile` for that sector |
| Index row `—` | Live index gateway returned no quotes for this request |
| FII/DII never | `institutional_flow` empty — run `POST /api/market/upstox-flows/refresh` after close |

## API

| Method | Path |
|--------|------|
| GET | `/v1/valuation-ratios/health` |
| GET | `/v1/valuation-ratios/coverage` |
| GET | `/v1/valuation-ratios/company/{symbol}` |
| POST | `/v1/valuation-ratios/ingest` |
| POST | `/v1/valuation-ratios/isin-backfill` |

BFF: `/api/intelligence/valuation-ratios/*` · `/api/market/company-isin/backfill`
