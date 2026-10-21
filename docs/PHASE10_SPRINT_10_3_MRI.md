# Phase 10 — Sprint 10.3: Macroeconomic Relationship Intelligence (MRI)

**Status:** Implemented in `intelligence-engine/macroeconomic_relationship_intelligence/`  
**Version:** 0.1.0  
**Depends on:** HMIP (10.2) historical series; soft-consumes timelines for confirmation  
**Pattern:** Macro twin of company Historical Relationship Intelligence (HRI)

---

## Objective

Discover, validate and maintain evidence-backed relationships between macroeconomic indicators, sectors, industries, companies and markets — so AGI understands **how macro variables influence everything else** before forecasting.

---

## Principle

Relationships must always be evidence-backed, versioned and traceable. Never inferred without supporting historical evidence. Never call external providers during retrieval.

---

## Pipeline

```text
Historical Macro Knowledge (HMIP)
Historical Company / Sector / Market Knowledge
        │
Relationship Discovery Engine
        │
Relationship Validation Engine
        │
Macro Relationship Graph
        │
Knowledge Retrieval Gateway → Forecast Intelligence
```

---

## Relationship kinds

- Macro → Company (Repo → HDFCBANK)
- Macro → Sector (CPI → FMCG, USDINR → IT Services)
- Macro → Market (Liquidity → NIFTY)
- Macro → Macro (Repo → CPI → GDP)
- Global → India (Fed → USDINR → FII → NIFTY)

---

## APIs

```text
GET  /v1/macro/relationships
GET  /v1/macro/relationships/{indicator}
GET  /v1/macro/relationships/company/{ticker}
GET  /v1/macro/relationships/sector/{sector}
GET  /v1/macro/relationships/graph
POST /v1/macro/relationships/run
GET  /v1/mri/health
GET  /v1/admin/macro-relationships
```

---

## Traces

`macro_relationship_discovery` · `macro_relationship_validation` · `macro_relationship_graph` · `macro_relationship_retrieval`

---

## Phase 10 progress

| Sprint | Module | Status |
|---|---|---|
| ✅ 10.1 | CMKP | Continuous ingestion |
| ✅ 10.2 | HMIP | Historical memory |
| ✅ 10.3 | MRI | Relationships |
| ➡️ 10.4 | HMAI | Analogues |
| 10.5 | MFI | Macro forecast scenarios |
