# Phase 10 — Sprint 10.1: Continuous Macroeconomic Knowledge Platform (CMKP)

**Status:** Implemented in `intelligence-engine/continuous_macro_knowledge/`  
**Version:** 0.1.0  
**Pattern:** Same as Company Intelligence continuous ingestion — background first

---

## Objective

Continuously acquire, validate, normalise and publish macroeconomic knowledge from official Indian and global sources into AGI's Macro Knowledge Store.

CMKP is **completely independent** of Ask, Research and Forecast. The Intelligence Engine must never fetch macro data during a user request.

---

## Principle

> Macroeconomic intelligence should behave exactly like company intelligence. Official macro releases continuously update AGI's institutional knowledge. User requests consume published macro knowledge—they never trigger data collection.

---

## Pipeline

```text
Official Sources
  RBI · MOSPI · NSO · MoF · CGA · SEBI · FRED · IMF · World Bank · OECD
        │
Continuous Macro Collectors
        │
Validation → Normalization → Macro Knowledge Objects
        │
Materiality Engine → Learning Engine
        │
Macro Knowledge Store → Knowledge Retrieval Gateway → Intelligence Engine
```

---

## Materiality

| Example | Result |
|---|---|
| Repo unchanged | **Ignore** (no learning) |
| Repo cut 50 bps | **High / Critical** → learning + forecast refresh hint |
| CPI surprise ≥ 0.15pp | **Medium+** → learning |

Knowledge objects are still published for immaterial updates; learning is filtered.

---

## APIs

```text
GET  /v1/macro/india
GET  /v1/macro/global
GET  /v1/macro/dashboard
GET  /v1/macro/indicator/{indicator}
GET  /v1/macro/releases
GET  /v1/macro/calendar
POST /v1/macro/run              # ops / scheduler only
GET  /v1/cmkp/health
GET  /v1/admin/macro-operations
```

Read APIs never collect. `POST /v1/macro/run` is the only ingestion entrypoint.

---

## Traces

`macro_collection` · `macro_validation` · `macro_normalization` · `macro_materiality` · `macro_learning` · `macro_publication`

---

## Soft wires

- Mission Control: `continuous_macro_knowledge` board
- IFI macro bundles: consume published CMKP via gateway when present (`providers_queried` stays empty)

## Phase 10 progress

| Sprint | Module | Status |
|---|---|---|
| ✅ 10.1 | CMKP | This sprint |
| ➡️ 10.2 | HMIP | Historical macro memory — see `PHASE10_SPRINT_10_2_HMIP.md` |
| 10.3 | MRI | Macro relationships |
| 10.4 | HMAI | Macro analogues |
| 10.5 | MFI | Macro forecast scenarios |
