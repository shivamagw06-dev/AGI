# Phase 12 — Sprint 12.2: Historical Market Intelligence Platform (HMKIP)

**Status:** Implemented in `intelligence-engine/historical_market_intelligence/`  
**Version:** 0.1.0  
**Pattern:** Market twin of HSIP / Macro HMIP  
**Note:** Programme short is **HMKIP** to avoid collision with Historical Macro Intelligence (**HMIP**).

---

## Objective

Acquire, validate, version and organise historical market knowledge into immutable **Historical Market Knowledge Objects** (HMKTOs).

HMKIP is AGIB's institutional memory of financial markets — cycles, breadth, liquidity, volatility, institutional flows, leadership and cross-asset behaviour — retrieved from the Knowledge Store without querying external providers during user requests.

---

## Architecture

```text
Groww Historical (ops) · Yahoo Finance Historical (ops)
        │
Historical Macro / Sector / Company Intelligence (soft)
        │
        ▼
Historical Market Builder
        │
Validation → Normalization → Immutable Publication → Timeline Builder
        │
Historical Market Knowledge Store → HMKIP_KRIG → Intelligence Engine / Investment Office
```

---

## Storage namespaces

`historical_market` · `historical_market_cycles` · `historical_market_breadth` · `historical_market_liquidity` · `historical_market_volatility` · `historical_market_flows` · `historical_market_leadership` · `historical_market_cross_asset`

Records are append-only and checksum-deduped. Revisions append new versions; nothing is overwritten.

---

## Guardrails

* Ask never collects or rebuilds history
* `providers_queried` always `[]` on read paths
* Groww / Yahoo reserved for ops seed provenance — never on Ask
* Soft-consumes CMKTP, HSIP and Macro HMIP tips during normalization only
* No BUY/SELL or target prices

---

## APIs

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/hmkip/health` | Programme health |
| GET | `/v1/market/history` | Historical observations |
| GET | `/v1/market/history/{market}` | Per-market history + timeline |
| GET | `/v1/market/history/timeline` | Institutional timelines |
| GET | `/v1/market/history/regimes` | Regime / cycle history |
| GET | `/v1/market/history/breadth` | Breadth history |
| GET | `/v1/market/history/liquidity` | Liquidity history |
| GET | `/v1/market/history/volatility` | Volatility history |
| GET | `/v1/market/history/flows` | Institutional flow history |
| GET | `/v1/market/history/search` | Searchable history |
| POST | `/v1/market/history/run` | Ops rebuild / backfill only |
| GET | `/v1/admin/historical-market` | HTML ops board |

---

## LangSmith traces

```text
historical_market_collection
historical_market_validation
historical_market_normalization
historical_market_timeline
historical_market_publication
historical_market_retrieval
```

---

## Mission Control

**Historical Market Operations** board (`phase: 12.2`):

* Historical coverage · Timeline completeness · Regime history · Breadth · Liquidity · Volatility · Flows · Cross-asset · Missing periods · Data quality · Knowledge freshness

---

## Soft consumers

* **IFI** soft-reads HMKIP for market historical intelligence (`HMKIP_KRIG`)
* Normalization soft-reads CMKTP / HSIP / Macro HMIP tips for provenance

---

## Phase 12 roadmap

| Sprint | Module | Status |
|---|---|---|
| ✅ 12.1 | CMKTP — Continuous Market Knowledge | Complete |
| ✅ 12.2 | HMKIP — Historical Market Intelligence | Complete |
| ✅ 12.3 | MKRI — Market Relationship Intelligence | Complete |
| ✅ 12.4 | HMKAI — Historical Market Analogue Intelligence | Complete |
| ✅ 12.5 | MKFI — Market Forecast Intelligence | Complete |
