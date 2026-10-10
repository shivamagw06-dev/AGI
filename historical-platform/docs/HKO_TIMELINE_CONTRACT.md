# Historical Knowledge Objects & Timeline Intelligence — Sprint 8.2

**Service:** AGI Historical Intelligence Platform (HIP)  
**Layer:** HKO + Timeline Intelligence  
**Version:** 0.2.0  
**Depends on:** Sprint 8.1 HAP  
**Boundary:** Organise history into structured knowledge and narratives. No pattern recognition (8.4), no analogues (8.5), no reasoning.

---

## 1. Objective

Convert raw historical market data into structured Historical Knowledge Objects and build chronological timelines for every company, sector, market and macro entity.

AGI should think in **historical narratives**, not rows of data.

---

## 2. Architecture

```text
Historical Acquisition Platform
            │
            ▼
Historical Knowledge Objects
            │
            ▼
Timeline Builder
            │
     ┌──────┼────────┐
     ▼      ▼        ▼
 Company  Sector   Market / Macro
 Timeline Timeline Timeline
     ▼
 Historical Knowledge Store
     ▼
 Knowledge Retrieval Gateway / Ask
```

---

## 3. Historical Knowledge Object types

| Type | Purpose |
|---|---|
| `HistoricalPrice` | OHLCV + adjusted close / market tip |
| `HistoricalFinancialStatement` | Revenue, EBITDA, PAT, EPS, margins, FCF |
| `HistoricalCorporateEvent` | Dated institutional events with importance |
| `HistoricalCorporateAction` | Dividend / split / bonus / rights / buyback |
| `HistoricalTimelineEvent` | Narrative timeline node (company/sector/market/macro) |

Versioning remains append-only — FY2018…FY2021 each remain available.

---

## 4. Timeline scopes

- **Company** — IPO, crises, leadership, COVID, margin cycles, AI transformation  
- **Sector** — crisis → digital → COVID surge → AI boom  
- **Market** — demonetisation → COVID crash → liquidity rally → inflation → election  
- **Macro** — RBI / inflation / GDP / budget / fiscal / currency cycles  

Every timeline event may link to related entities (COVID → IT Demand → Infosys → Revenue → Margins → Valuation).

---

## 5. Integrity

1. Never overwrite historical records  
2. Corrections are new versions  
3. Timelines are regenerated from immutable HKO + institutional seed narrative  
4. Retrieval never queries Yahoo / NSE / BSE / Company IR  

---

## 6. APIs

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

Legacy Sprint 8.1 paths under `/v1/historical/*` remain.

---

## 7. Success criteria

- Every company has a versioned historical timeline  
- Prices, financials, events, actions stored as HKO  
- Timelines retrievable without external providers  
- Records immutable and versioned  
- IE can answer timeline questions (e.g. Compare Infosys today with FY2018) from store only  
