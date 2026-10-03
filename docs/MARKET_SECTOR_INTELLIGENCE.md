# AGI Market & Sector Intelligence Terminal v1.0

Institutional market overview: **Warehouse → Unified Valuation Engine → Market Intelligence Engine → Terminal**.

No UI calculations. No buy/sell recommendations — research priorities only.

## Architecture

```
Institutional Warehouse
        ↓
Unified Valuation Engine (multiples, percentiles, attribution)
        ↓
Market Intelligence Engine
        ↓
Market & Sector Intelligence Terminal (/market-sector-intelligence)
```

## Market Intelligence Engine

Package: `intelligence-engine/market_intelligence_engine/`

| Module | Responsibility |
|--------|----------------|
| `universe.py` | Load NSE universe from warehouse + valuation engine |
| `aggregation.py` | Market overview, sector/industry tables, heatmap bands |
| `breadth.py` | Advance/decline from `daily_market_history` |
| `flows.py` | FII/DII from warehouse `institutional_flow` tab |
| `opportunities.py` | Relative value, historical discount/premium, quality, re-rating |
| `rotation.py` | Sector rotation + market explainability |
| `summary.py` | AGI market summary (interpretive, not prescriptive) |
| `ingest_flows.py` | Upstox FII/DII → warehouse via DQIV gateway |

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/market-intelligence/health` | Engine health |
| GET | `/v1/market-intelligence/dashboard` | Full dashboard pack |
| GET | `/v1/market-intelligence/sector/{sector}` | Sector drill-down |
| POST | `/v1/market-intelligence/flows/ingest` | Ingest FII/DII rows |

BFF: `/api/intelligence/market-intelligence/*`

## Institutional flow ingest

1. BFF `POST /api/market/upstox-flows/refresh` fetches Upstox FII/DII
2. Posts normalized rows to engine ingest
3. Warehouse tab `institutional_flow` stores history
4. Dashboard reads warehouse only (never Upstox from UI)

## UI sections

1. Market Overview + AGI summary
2. Sector Valuation Heatmap (historical percentile bands)
3. Market Breadth
4. Institutional Flow (FII/DII)
5. Sector Intelligence table
6. Industry Intelligence table
7. Opportunity Dashboard
8. Market Rotation
9. Research Priorities
10. Market Explainability
11. Coverage & Provenance

## Acceptance

- [x] No UI-level valuation math
- [x] Widgets read valuation engine + warehouse
- [x] FII/DII warehouse path before display
- [x] Sector metrics historically aware (percentiles)
- [x] Opportunities include evidence + priority
- [x] Provenance on pack
- [x] No buy/sell language
