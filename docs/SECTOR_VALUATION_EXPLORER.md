# Institutional Valuation Research Workspace v2.0

**Route:** `/valuation-terminal` · `/admin/valuation-terminal`  
**Engine:** `intelligence-engine/sector_valuation_explorer/` (v2.0)  
**UI:** Market snapshot · sector directory · industry workspace · company table · research boards inside Valuation Terminal

## Flow

```text
Indian Market → Sector → Industry → Company → Historical Valuation → Research Intelligence
```

Company search and favorites remain available. Analysts can also start from the market snapshot or All Sectors.

## Data path

```text
Institutional Warehouse
  → Unified Valuation Engine
  → HVIE
  → VPAE
  → DQIV / Market Intelligence universe
  → Sector Valuation Explorer APIs
  → Valuation Research Workspace UI
```

No UI calculations. No direct vendor calls. No BUY / SELL / target price language.

## APIs

| Route | Purpose |
|---|---|
| `GET /v1/valuation/market` | Indian market valuation snapshot |
| `GET /v1/valuation/sectors` | Sector directory cards |
| `GET /v1/valuation/sector/{sector}` | Full sector workspace pack |
| `GET /v1/valuation/sector/{sector}/industries` | Industry cards for a sector |
| `GET /v1/valuation/industry/{industry}` | Industry workspace pack |
| `GET /v1/valuation/sector/{sector}/summary` | Dashboard + explanation + outcome |
| `GET /v1/valuation/sector/{sector}/companies` | Filterable company table |
| `GET /v1/valuation/sector/{sector}/leaders` | Top-10 leaderboards |
| `GET /v1/valuation/sector/{sector}/heatmap` | Percentile color cells |
| `GET /v1/valuation/sector/{sector}/research` | Research priorities |
| `GET /v1/valuation/sector/{sector}/rotation` | Sector rotation context |
| `GET /v1/valuation/opportunities` | Opportunity boards (top 10) |
| `GET /v1/valuation/premium` | Premium dashboard |
| `GET /v1/valuation/rerating` | Re-rating transitions |
| `GET /v1/valuation/company/{symbol}` | UVE terminal company pack |
| `GET /v1/valuation/company/{symbol}/history` | HVIE history |

Mirrored under `/api/intelligence/valuation/*`.

## Workspace sections

1. **Market valuation snapshot** — coverage, median PE/PB/EV/EBITDA/ROE/ROCE, historical percentile, regime, research focus
2. **Sector directory** — searchable/sortable cards with premium, coverage, confidence
3. **Sector workspace** — dashboard, explanation (`sector_lens`), institutional outcome
4. **Industry workspace** — clickable industry cards between sector and company
5. **Company valuation table** — current vs sector/industry, historical %, status, provenance tips
6. **Institutional filters** — historically cheap/expensive, caps, ROE/ROCE, coverage/confidence
7. **Opportunity / premium / re-rating boards** — warehouse-backed research screens
8. **Sector rotation** — valuation + PE change + flow context
9. **AI research priorities** — investigation worklists (not recommendations)
10. **Export** — CSV, copy table, copy research summary

## Design rules

- Reuse `valuation_terminal.sector_lens` — do not duplicate metric applicability
- Every metric exposes source / coverage / confidence where available
- Historical conclusions respect HVIE span guards
- Company-first and sector-first navigation coexist (`?sector=` · `?industry=` · `?symbol=`)

## Acceptance

- Users can begin from market, sector, industry, or company
- Sector cards show live valuation + historical context
- Industry layer sits between sector and company
- Opportunity, premium, re-rating, and rotation boards are warehouse-backed
- No UI-side calculations and no direct vendor access
