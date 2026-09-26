# Historical Analogue Intelligence — Sprint 8.4

**Service:** AGI Historical Intelligence Platform (HIP)  
**Layer:** HAI — Historical Analogue Engine  
**Version:** 0.4.0  
**Depends on:** Sprint 8.3 HRI (+ 8.2 timelines, 8.1 HAP)  
**Boundary:** Analogue reasoning only — not forecasting, not pattern/cycle detection (8.5).

---

## 1. Objective

Answer: **"Have we ever seen this before?"**

Search historical knowledge for situations that resemble the current company, sector, market or macro environment. Rank by deterministic multi-dimension similarity with explainable scores and evidence.

---

## 2. Architecture

```text
Current Knowledge
        │
        ▼
Analogue Query Builder
        │
        ▼
Historical Analogue Engine
        │
 ┌──────┼────────┬────────┐
 ▼      ▼        ▼        ▼
Company Sector  Market  Macro
History History History History
        │
        ▼
Similarity Scoring Engine
        │
        ▼
Ranked Historical Analogues
        │
        ▼
KRIG → Intelligence Engine
```

---

## 3. Integrity

1. Every analogue has an explainable similarity score (0–100)  
2. Matching and non-matching dimensions are always returned  
3. Supporting evidence required (financials / timeline / relationships)  
4. Links back to timelines and relationships when available  
5. Retrieval never queries external providers  

---

## 4. APIs

```text
GET  /v1/history/analogues/company/{symbol}
GET  /v1/history/analogues/sector/{sector}
GET  /v1/history/analogues/market
GET  /v1/history/analogues/macro
POST /v1/history/analogues/search
```

Success path:

> Has Infosys experienced this type of slowdown before?

```bash
curl -X POST http://127.0.0.1:8092/v1/history/analogues/search \
  -H 'content-type: application/json' \
  -d '{"scope":"company","entity":"INFY","question":"Has Infosys experienced this type of slowdown before?","top_k":5}'
```

---

## 5. Traces

- `historical_analogue_search`
- `similarity_scoring`
- `analogue_ranking`
- `analogue_retrieval`

---

## 6. Success criteria

- Analogues for company / sector / market / macro  
- Deterministic ranked similarity  
- Evidence + timeline/relationship links  
- IE consumes bundles with `providers_queried: []`  
- No analogue without explainable score and evidence  
