# Historical Relationship Intelligence — Sprint 8.3

**Service:** AGI Historical Intelligence Platform (HIP)  
**Layer:** HRI — Historical Relationship Graph  
**Version:** 0.3.0  
**Depends on:** Sprint 8.2 HKO + Timeline Intelligence  
**Boundary:** Cause-and-effect / structural historical links only. No pattern engines (8.4), no analogues (8.5).

---

## 1. Objective

Connect companies, sectors, macro events, corporate events and market behaviour across time so AGI understands **how one event influenced another**.

---

## 2. Architecture

```text
Historical Knowledge Objects
            │
            ▼
Historical Relationship Engine
            │
            ▼
Entity Relationship Builder
            │
    ┌───────┼────────┬──────────┐
    ▼       ▼        ▼          ▼
 Company  Sector   Market    Macro
 Links     Links    Links      Links
            │
            ▼
Historical Relationship Graph
            │
            ▼
Knowledge Retrieval Gateway → Intelligence Engine
```

---

## 3. Integrity rules

1. **No relationship without evidence** — validation rejects empty evidence  
2. Every published edge records: source, target, type, direction, confidence, first observed, last confirmed, supporting evidence  
3. Relationships are versioned (`relationship_versions`)  
4. Retrieval never queries Yahoo / NSE / BSE / Company IR  

---

## 4. Relationship types

Company: Competitor, Supplier, Customer, Parent, Subsidiary, Joint Venture, Acquisition Target, Global Peer, Revenue Sensitivity, Demand Driver  

Sector: Sector Leader, Sector Peer, Sector Beneficiary, Sector Under Pressure  

Macro/Market: Positive/Negative Historical Impact, Transmission, Caused, Affected, Beneficiary, Under Pressure  

---

## 5. Storage

```text
historical_relationships
company_relationships
sector_relationships
macro_relationships
market_relationships
relationship_evidence
relationship_versions
```

---

## 6. APIs

```text
GET  /v1/history/relationships/company/{symbol}
GET  /v1/history/relationships/sector/{sector}
GET  /v1/history/relationships/macro/{event}
GET  /v1/history/relationships/market
POST /v1/history/relationships/explain
```

Success path:

> How have RBI rate cuts historically affected HDFC Bank?

```bash
curl -X POST http://127.0.0.1:8092/v1/history/relationships/explain \
  -H 'content-type: application/json' \
  -d '{"source":"RBI Rate Cut","target":"HDFCBANK"}'
```

---

## 7. Traces

- `historical_relationship_builder`
- `relationship_validation`
- `relationship_publication`
- `relationship_retrieval`

---

## 8. Success criteria

- Relationships created from validated historical knowledge + evidence-backed catalog  
- Every published relationship is evidence-backed, versioned, confidence-scored  
- Company / sector / market / macro connected in the graph  
- IE retrieves relationships with `providers_queried: []`  
- No publication without traceable evidence  
