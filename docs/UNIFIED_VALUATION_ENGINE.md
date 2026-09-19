# Unified Valuation Engine v3.0

**Status:** Core + Valuation Terminal migration
**Reads:** `institutional_warehouse` only
**Module:** `intelligence-engine/valuation_engine/`

## Why it exists

Three surfaces produced valuation numbers independently:

| Surface | Source (before) |
|---|---|
| Valuation Terminal | committed Yahoo JSON under `market_data/` (retired) |
| `valuation_intelligence` (Ask) | live quote plus NSE filings, composed per request |
| `historical_valuation` warehouse tab | computed by the formula engine, displayed nowhere |

Three P/E numbers for one company could disagree, and nothing on screen
explained why. This engine is the single place a multiple is computed. The
Institutional Valuation Terminal now reads only this engine.

## Flow

```
Upstox / Yahoo / Capital IQ
        ↓
      DQIV gateway
        ↓
      Warehouse
        ↓
Unified Valuation Engine
        ↓
Terminal · Ask · Hedge Fund · Research
```

The engine never calls a vendor. Changing a provider changes what the warehouse
holds, not how a multiple is computed — so a source swap needs no engine change.

## Dependency graph

Metrics are declared as a graph rather than a call order (`graph.py`). This buys
three things:

- **Partial recompute.** A quote tick dirties `cmp` and its dependents. Statement
  inputs that did not move are not rebuilt, so refreshing prices does not
  recompute the market.
- **Explainable nulls.** A missing figure names the input it lacked rather than
  rendering as a blank cell. On a valuation screen, blank and zero are very
  different claims.
- **Derived ordering.** Adding a metric cannot silently depend on something
  computed after it; `topological()` decides the order.

```
cmp ──┬─→ market_cap ──→ enterprise_value ──→ ev_ebitda
      ├─→ pe                                └─→ ev_sales
      ├─→ pb
      └─→ dividend_yield
```

## Units

Statement aggregates live in INR million; price and share count are in rupees.
The engine converts aggregates once, on read, so every multiple divides rupees
by rupees. See the Units section of `INSTITUTIONAL_DATA_WAREHOUSE.md`.

## Sector applicability / valuation policy

Whether a metric means anything for a business is decided by the
**Valuation Policy & Applicability Engine (VPAE)** — Phase 8.2A — in
`valuation_policy/`. VPAE extends `valuation_terminal.sector_lens` (industry DNA
baseline) with instrument type, profitability, coverage and DQIV.

UVE computes multiples; VPAE decides what may be shown. A bank returns
`meaningful: false` for EV/EBITDA rather than a number nobody should read. See
`docs/VALUATION_POLICY_APPLICABILITY_ENGINE.md`.

## Provenance

Read from row metadata, never hardcoded:

```json
"provenance": {
  "price":      {"source": "groww", "updated_at": "...", "version": 3},
  "financials": {"source": "upstox_fundamentals", "reported_unit": "crore"},
  "consensus":  {"source": "capital_iq"},
  "formula_version": "3.0"
}
```

A row states its own source, so the display stays correct when a new provider
starts writing. Every computed value also carries the sources of its inputs.

## Valuation change log

Terminals report that P/E fell from 18.4 to 17.9 and leave the analyst to work
out why. Because each figure declares what it was computed from, the cause is
derivable — compare inputs across two observations and name the ones that moved:

> `pe` moved -2.7% because cmp declined 2.7%, with eps unchanged.

Moves below `MATERIAL_PCT` (0.5%) are not narrated, so noise is not reported as
a cause. The engine states the arithmetic and stops; *why* the price moved is a
question for the research layer.

## API

```bash
GET  /v1/valuation-engine/health
GET  /v1/valuation-engine/company/{symbol}
POST /v1/valuation-engine/explain-change  {"symbol", "before", "after"}

GET  /v1/valuation-engine/terminal/health
GET  /v1/valuation-engine/terminal/search?q=
GET  /v1/valuation-engine/terminal/company/{symbol}
GET  /v1/valuation-engine/terminal/series/{symbol}/{metric}
GET  /v1/valuation-engine/terminal/explain/{metric}
```

`get_company_valuation` returns metrics, sector and historical context,
coverage and provenance in one response, so a consumer never stitches several
calls and re-derives the same multiple differently. The terminal pack adds the
institutional table, peers, charts coverage, change log, DQIV surface and
Valuation Health Score.

## Coverage

Counted only over metrics that apply to the business, and every unavailable
metric states what it lacked:

```json
"coverage": {"applicable": 11, "available": 9, "pct": 81.8,
             "unavailable": {"forward_pe": "needs forward_eps"}}
```

## Not yet done

- Market / Sector / Opportunity dashboards (next PR)
- Daily research narratives and briefs
- Historical re-rating / timeline intelligence
- Portfolio valuation, watchlists, alerts
- Ask path still composes some live quotes independently (cut over later)
