# Phase 8 — Sprint 8.2: Historical Knowledge Objects & Timeline Intelligence

**Status:** Implemented in `historical-platform/` (HIP v0.2.0)  
**Depends on:** Sprint 8.1 HAP  
**Out of scope:** Pattern recognition (8.4), historical analogues (8.5), relationship graph expansion beyond timeline links (8.3)

---

## Objective

Convert acquired historical records into structured **Historical Knowledge Objects** and chronological **timelines** so AGI reasons over historical narratives, not provider rows.

---

## Architecture

```text
Historical Acquisition Platform (8.1)
            │
            ▼
Historical Knowledge Objects (shaped views)
            │
            ▼
Timeline Builder (company / sector / market / macro)
            │
            ▼
Historical Knowledge Store (append-only HKO + narrative timelines)
            │
            ▼
Historical Retrieval Gateway → KRIG soft bridge → Ask / IE
```

---

## HKO types

| Object | Fields (canonical) |
|---|---|
| HistoricalPrice | Company, Date, OHLCV, Market Cap, Adjusted Close, Source |
| HistoricalFinancialStatement | Company, Quarter/FY, Revenue, EBITDA, PAT, EPS, Margins, FCF, Source |
| HistoricalCorporateEvent | Company, Date, Event Type, Description, Importance, Source |
| HistoricalCorporateAction | Dividend / Split / Bonus / Rights / Buyback, Dates, Source |
| HistoricalTimelineEvent | Scope, Subject, Year, Title, Importance, Links |

Versioning is append-only: FY2018…FY2025 each remain available.

---

## Timeline scopes

- **Company** — e.g. Infosys: IPO → GFC → Leadership → COVID → Margin Compression → AI  
- **Sector** — e.g. IT Services: Crisis → Digital → COVID Surge → AI Boom  
- **Market** — NIFTY: Demonetisation → COVID Crash → Liquidity Rally → Inflation → Election  
- **Macro** — India: RBI / inflation / GDP / budget / fiscal / currency cycles  

Timeline links encode transmission chains (COVID → IT Demand → Infosys → Revenue → Margins → Valuation).

---

## APIs

```text
GET  /v1/history/company/{symbol}
GET  /v1/history/timeline/{symbol}
GET  /v1/history/financials/{symbol}
GET  /v1/history/events/{symbol}
POST /v1/history/compare
GET  /v1/history/timeline/sector/{sector}
GET  /v1/history/timeline/market
GET  /v1/history/timeline/macro
GET  /v1/history/mission-control
```

Legacy `/v1/historical/*` paths from 8.1 remain.

Bootstrap rebuilds timelines:

```bash
curl -X POST http://127.0.0.1:8092/v1/internal/bootstrap
curl http://127.0.0.1:8092/v1/history/timeline/INFY
curl -X POST http://127.0.0.1:8092/v1/history/compare \
  -H 'content-type: application/json' \
  -d '{"symbol":"INFY","as_of_period":"FY2018"}'
```

---

## Mission Control

`GET /v1/history/mission-control` — Historical Intelligence board:

- Coverage by company  
- Timeline completeness  
- Years ingested / missing periods  
- Ingestion progress  
- Retrieval performance (`providers_queried` always `[]`)  

---

## LangSmith-style traces

- `historical_ingestion`  
- `historical_normalization`  
- `timeline_generation`  
- `historical_retrieval`  

---

## Success criteria

| Criterion | Evidence |
|---|---|
| Versioned company timelines | `/v1/history/timeline/INFY` narrative anchors |
| HKO storage | Shaped `hko` on financials / events / prices |
| Retrievable without providers | All history APIs return `providers_queried: []` |
| Immutable + versioned | Duplicate checksums rejected; FY periods retained |
| Timeline Q&A from store | `/v1/history/compare` Infosys vs FY2018 |

---

## Roadmap after 8.2

| Sprint | Module | Goal |
|---|---|---|
| ✅ 8.1 | HAP | Bulk historical ingestion |
| ✅ 8.2 | HKO + Timeline Intelligence | Structured historical memory |
| 8.3 | Historical Relationship Engine | Cross-entity historical links |
| 8.4 | Pattern & Cycle Intelligence | Recurring patterns |
| 8.5 | Historical Analog Intelligence | Similar-situation retrieval |
