# Phase 11 — Sprint 11.3: Sector Relationship Intelligence (SRI)

**Status:** Implemented in `intelligence-engine/sector_relationship_intelligence/`  
**Version:** 0.1.0  
**Depends on:** CSKP (11.1) universe; soft-consumes HSIP / HMIP / MRI tips  
**Enables:** HSAI (11.4) analogues; SFI (11.5) sector forecasts

---

## Objective

Build the **Sector Relationship Intelligence (SRI)** engine that discovers, validates and maintains evidence-backed relationships between macroeconomic indicators, sectors, industries, companies and financial markets.

Relationships are evidence-backed, versioned, explainable and continuously updated. Ask never rebuilds or collects.

---

## Architecture

```text
Historical Macro Intelligence
        │
Historical Sector Intelligence
        │
Historical Company Intelligence
        │
Historical Market Intelligence
        │
Research Knowledge
        │
        ▼
Sector Relationship Discovery Engine
        │
Relationship Validation Engine
        │
Evidence Scoring Engine
        │
Sector Relationship Graph
        │
Knowledge Retrieval Gateway
        │
Forecast Intelligence
```

---

## Relationship kinds

| Kind | Example |
|---|---|
| `macro_to_sector` | Repo Rate → Banking |
| `sector_to_sector` | Banking → Real Estate → Cement |
| `sector_to_company` | IT Services → INFY |
| `company_to_sector` | Reliance → Oil & Gas |
| `sector_to_market` | Banking → NIFTY |
| `global_to_sector` | Fed Funds → IT / Pharma |

Every published edge requires supporting evidence, historical observations, confidence, lag, provenance and version.

---

## APIs

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/sri/health` | Programme health |
| GET | `/v1/sector/relationships` | All published relationships |
| GET | `/v1/sector/relationships/{sector}` | Sector endpoint |
| GET | `/v1/sector/relationships/company/{ticker}` | Company endpoint |
| GET | `/v1/sector/relationships/graph` | Nodes, edges, transmission paths |
| GET | `/v1/sector/relationships/search` | `q` / `kind` / source / target |
| GET | `/v1/sector/relationships/dashboard` | Mission Control board payload |
| POST | `/v1/sector/relationships/run` | Ops rebuild only |
| GET | `/v1/admin/sector-relationships` | HTML ops board |

Read APIs never rebuild. `providers_queried` is always `[]`.

---

## LangSmith traces

```text
sector_relationship_discovery
sector_relationship_validation
sector_relationship_graph
sector_relationship_retrieval
sector_relationship_refresh
```

---

## Mission Control

**Sector Relationship Intelligence** board (`phase: 11.3`):

* Total / active relationships
* Confidence distribution
* Recently validated & newly discovered
* Coverage by sector
* Freshness / stale sample
* Validation failures

---

## Soft consumers

* **IFI** soft-reads SRI for sector `relationship_intelligence` (store-only, never rebuilds).
* SRI soft-confirms via HSIP timelines, HMIP indicator timelines, and MRI macro→sector tips when available.

---

## Success criteria

* Relationships between macro, sectors, companies and markets are discovered and validated from the evidence catalog.
* Every relationship includes evidence, confidence, lag, provenance and version history.
* Sector Relationship Graph is searchable and exposes transmission paths.
* Forecast paths can consume validated relationships without external providers.
* Quality / coverage / health observable via Mission Control and LangSmith traces.

---

## Phase 11 progress

| Sprint | Module | Status |
|---|---|---|
| ✅ 11.1 | CSKP | Continuous sector knowledge |
| ✅ 11.2 | HSIP | Historical sector memory |
| ✅ 11.3 | SRI | Sector relationship intelligence |
| ✅ 11.4 | HSAI | Historical sector analogue intelligence |
| ✅ 11.5 | SFI | Sector forecast intelligence |

### Architectural symmetry

```text
Continuous Knowledge
        │
        ▼
Historical Knowledge
        │
        ▼
Relationship Intelligence
        │
        ▼
Historical Analogues
        │
        ▼
Forecast Intelligence
```

Company, Macro and Sector domains now share this ladder through Sprint 11.3.
