# Valuation Attribution & Research Intelligence Engine (VARIE) v1.0

**Engine:** `intelligence-engine/valuation_attribution_engine/`  
**UI:** Why Valuation? panels in Valuation Research Workspace  
**Rule:** Explain *why* valuation is where it is — never invent causes, never BUY/SELL

## Architecture

```text
Institutional Warehouse
  → Unified Valuation Engine (attribution graph)
  → HVIE (history, regimes, re-rating)
  → VPAE / sector_lens context (via MI)
  → Market Intelligence (universe, flows)
  → VARIE
  → Terminal / Ask / Portfolio / Market Intelligence
```

VARIE performs **no valuation calculations**. It explains outputs already produced by AGIB and ranks observed evidence.

## Evidence kinds

| Kind | Meaning |
|---|---|
| `observed` | Direct warehouse / HVIE / MI observation (ROE change, ownership pp, PE change) |
| `derived` | Relative evidence weights scaled to an observed premium/discount, or HVIE regime path |
| `inferred` | Market-level context (e.g. FII/DII) applied cautiously |

If evidence is insufficient:

> Primary driver cannot be determined from available data.

## APIs

| Route | Purpose |
|---|---|
| `GET /v1/valuation/attribution/company/{symbol}` | Why Valuation pack |
| `GET /v1/valuation/attribution/sector/{sector}` | Sector drivers |
| `GET /v1/valuation/attribution/industry/{industry}` | Industry drivers |
| `GET /v1/valuation/attribution/market` | Market premium contributors |
| `GET /v1/valuation/attribution/peer/{symbol}` | Peer difference reasons |
| `GET /v1/valuation/attribution/history/{symbol}` | Expansion / compression narrative |
| `GET /v1/valuation/attribution/timeline/{symbol}` | Regime + research timeline |
| `GET /v1/valuation/attribution/opportunities` | Cheap/expensive *with reasons* |
| `GET /v1/valuation/attribution/leaders` | Re-rating / ROE leaderboards |

Mirrored under `/api/intelligence/valuation/attribution/*`.

## UI

1. **Market attribution strip** on the research workspace home
2. **Sector attribution panel** inside the sector workspace
3. **Company Why Valuation?** panel on company drill-down — premium breakdown, daily change, opportunity/risk, research note, regime timeline, clickable drivers

## Acceptance

- Every company valuation surfaces a Why Valuation? panel
- Premiums/discounts decompose into evidence-backed factors (or explicitly residual)
- Daily moves use UVE attribution materiality (0.5%)
- No UI-side calculations, no vendor calls, no recommendation language
