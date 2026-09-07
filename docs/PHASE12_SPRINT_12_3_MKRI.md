# Phase 12 — Sprint 12.3: Market Relationship Intelligence (MKRI)

**Status:** Implemented in `intelligence-engine/market_relationship_intelligence/`  
**Version:** 0.1.0  
**Pattern:** Market twin of SRI / Macro MRI  
**Note:** Programme short is **MKRI** to avoid collision with Macroeconomic Relationship Intelligence (**MRI**).

---

## Objective

Continuously discover, validate and maintain evidence-backed relationships across market regimes, macroeconomic variables, sectors, industries, companies, asset classes and institutional flows.

MKRI enables AGIB to understand how market changes propagate through the financial system — the foundation for Market Forecast Intelligence.

---

## Architecture

```text
HMKIP · HMIP · HSIP · Company History · Research
                │
                ▼
Market Relationship Discovery Engine
                │
Validation → Evidence Scoring → Market Relationship Graph
                │
MKRI_KRIG → Forecast Intelligence / Investment Office
```

---

## Relationship kinds

`macro_to_market` · `market_to_sector` · `sector_to_market` · `market_to_company` · `cross_asset` · `flows` · `volatility`

Every published relationship includes confidence, historical observations, average lag, supporting / contradictory evidence, provenance and version history. Relationships without sufficient evidence are rejected.

---

## Guardrails

* Ask never rebuilds the graph
* `providers_queried` always `[]` on read paths
* Soft-consumes HMKIP / HMIP / HSIP / Macro MRI tips during enrichment only
* No BUY/SELL or target prices
* No hard-coded rules without historical evidence

---

## APIs

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/mkri/health` | Programme health |
| GET | `/v1/market/relationships` | All published relationships |
| GET | `/v1/market/relationships/{indicator}` | By indicator / node |
| GET | `/v1/market/relationships/sector/{sector}` | Sector endpoint |
| GET | `/v1/market/relationships/company/{ticker}` | Company endpoint |
| GET | `/v1/market/relationships/graph` | Graph + optional transmission paths |
| GET | `/v1/market/relationships/search` | Searchable graph |
| GET | `/v1/market/relationships/dashboard` | Mission Control JSON |
| POST | `/v1/market/relationships/run` | Ops rebuild only |
| GET | `/v1/admin/market-relationships` | HTML ops board |

---

## LangSmith traces

```text
market_relationship_discovery
market_relationship_validation
market_relationship_scoring
market_relationship_graph
market_relationship_refresh
market_relationship_retrieval
```

---

## Mission Control

**Market Relationship Intelligence** board (`phase: 12.3`):

* Total / active relationships · Coverage · Confidence distribution · Recently validated · Newly discovered · Freshness · Validation failures · Graph health · Coverage by market / sector / asset class

---

## Soft consumers

* **IFI** soft-reads MKRI for market relationship intelligence (`MKRI_KRIG`)
* Enrichment soft-reads HMKIP / HMIP / HSIP / Macro MRI tips

---

## Connected graphs

At this stage AGIB maintains three mature relationship graphs:

* **Macro Relationship Graph** (MRI)
* **Sector Relationship Graph** (SRI)
* **Market Relationship Graph** (MKRI)

---

## Phase 12 roadmap

| Sprint | Module | Status |
|---|---|---|
| ✅ 12.1 | CMKTP — Continuous Market Knowledge | Complete |
| ✅ 12.2 | HMKIP — Historical Market Intelligence | Complete |
| ✅ 12.3 | MKRI — Market Relationship Intelligence | Complete |
| ✅ 12.4 | HMKAI — Historical Market Analogue Intelligence | Complete |
| ✅ 12.5 | MKFI — Market Forecast Intelligence | Complete |
