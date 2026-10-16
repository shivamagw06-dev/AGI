# Phase 11 — Sprint 11.1: Continuous Sector Knowledge Platform (CSKP)

**Status:** Implemented in `intelligence-engine/continuous_sector_knowledge/`  
**Version:** 0.1.0  
**Pattern:** Macro twin of CMKP — event-driven derived sector knowledge  
**Sits between:** Macro Intelligence → **Sector** → Company Intelligence

---

## Objective

Continuously acquire, validate and publish institutional Sector Knowledge Objects for every supported Indian sector. Sector knowledge is **derived** from company, macro, market, event and research tips — never polled from external APIs on a fixed timer, and never constructed during Ask.

---

## Architecture

```text
Company Knowledge
Macro Knowledge (CMKP)
Market Knowledge
Corporate Events
Research (+ MRI tips)
        │
        ▼
Sector Intelligence Builder
        │
Validate → Normalize → Materiality → Learning → Publish
        │
Sector Knowledge Store → KRIG → Intelligence Engine
```

---

## Supported sectors (31)

Banking, Financial Services, NBFC, Insurance, IT Services, Software Products, Pharma, Healthcare, FMCG, Retail, Auto, Auto Ancillary, Capital Goods, Industrials, Cement, Metals, Mining, Oil & Gas, Chemicals, Specialty Chemicals, Defence, Power, Utilities, Renewable Energy, Telecom, Infrastructure, Real Estate, Aviation, Logistics, Textiles, Consumer Durables.

---

## Collection behaviour

Event-driven refresh when:

- Company knowledge changes materially
- Macro knowledge changes materially (e.g. RBI rate cut → Banking)
- Government policy / significant sector events
- Earnings season updates
- Major M&A / competitive dynamics

Ops entrypoint: `POST /v1/sector/run` (optional `trigger`, `sectors`).

---

## APIs

```text
GET  /v1/sector
GET  /v1/sector/{sector}
GET  /v1/sector/dashboard
GET  /v1/sector/leaders
GET  /v1/sector/comparison
GET  /v1/sector/calendar
POST /v1/sector/run
GET  /v1/cskp/health
GET  /v1/admin/sector-operations
```

---

## Traces

`sector_collection` · `sector_normalization` · `sector_learning` · `sector_publication` · `sector_refresh`

---

## Mission Control

**Sector Operations** board: health, coverage, freshness, latest events, material updates, research coverage, learning events, company coverage by sector.

---

## Phase 11 roadmap

| Sprint | Module | Status |
|---|---|---|
| ✅ 11.1 | CSKP | Continuous sector knowledge |
| ✅ 11.2 | HSIP | Historical sector memory |
| ✅ 11.3 | SRI | Sector relationship intelligence |
| ✅ 11.4 | HSAI | Historical sector analogue intelligence |
| ✅ 11.5 | SFI | Sector forecast intelligence |
