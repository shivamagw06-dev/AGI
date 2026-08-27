# Phase 10 — Sprint 10.2: Historical Macroeconomic Intelligence Platform (HMIP)

**Status:** Implemented in `intelligence-engine/historical_macro_intelligence/`  
**Version:** 0.1.0  
**Depends on:** Sprint 10.1 CMKP (continuous tip)  
**Pattern:** Company historical intelligence — immutable memory after continuous ingestion

---

## Objective

Acquire, validate, version and organise historical macroeconomic data into AGI's Historical Macro Knowledge Store so AGI can reason across decades of policy, inflation, GDP, fiscal and markets **without querying external providers during analysis**.

---

## Principle

Historical macro knowledge is **immutable** and forms AGI's long-term institutional memory.

---

## Pipeline

```text
Official Historical Sources
  RBI · MOSPI · NSO · MoF · CGA · SEBI · FRED · IMF · World Bank · OECD
        │
Historical Macro Collectors
        │
Validate → Normalize → Historical Macro Knowledge Objects
        │
Timeline Builder → Historical Macro Knowledge Store → Gateway → IE
```

---

## Storage namespaces

`historical_macro` · `historical_inflation` · `historical_rates` · `historical_gdp` · `historical_iip` · `historical_fiscal` · `historical_trade` · `historical_liquidity` · `historical_forex` · `historical_budget`

Records are append-only. Identical re-ingest is checksum-deduped. Revisions append new versions.

---

## APIs

```text
GET  /v1/macro/history
GET  /v1/macro/history/{indicator}
GET  /v1/macro/history/country/{country}
GET  /v1/macro/history/timeline
GET  /v1/macro/history/search
GET  /v1/macro/history/dashboard
POST /v1/macro/history/run
GET  /v1/hmip/health
GET  /v1/admin/historical-macro
```

---

## Traces

`historical_macro_collection` · `historical_macro_validation` · `historical_macro_normalization` · `historical_macro_publication` · `historical_macro_retrieval`

---

## Phase 10 progress

| Sprint | Module | Status |
|---|---|---|
| ✅ 10.1 | CMKP | Continuous macro ingestion |
| ✅ 10.2 | HMIP | Historical macro memory |
| ✅ 10.3 | MRI | Macro relationships — see `PHASE10_SPRINT_10_3_MRI.md` |
| ➡️ 10.4 | HMAI | Macro analogues |
| 10.5 | MFI | Macro forecast scenarios |
