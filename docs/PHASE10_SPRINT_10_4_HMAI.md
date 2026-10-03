# Phase 10 — Sprint 10.4: Historical Macro Analogue Intelligence (HMAI)

**Status:** Implemented in `intelligence-engine/historical_macro_analogue_intelligence/`  
**Version:** 0.1.0  
**Depends on:** CMKP (10.1) current tip · HMIP (10.2) historical series · MRI (10.3) relationship evidence  
**Pattern:** Macro twin of company Historical Analogue Intelligence (HAI)

---

## Objective

Identify and rank historical macroeconomic environments most similar to current conditions so AGI can answer:

> **Have we seen this macro environment before?**

Analogues are deterministic, explainable and fully traceable to historical evidence.

---

## Architecture

```text
Current Macro Knowledge (CMKP)
        │
Historical Macro Knowledge (HMIP)
        │
Macro Relationship Graph (MRI)
        │
Macro Research tips
        │
        ▼
Macro Analogue Engine
        │
Similarity Engine → Ranking Engine
        │
Historical Macro Analogues
        │
Knowledge Retrieval Gateway → Forecast Intelligence (10.5)
```

---

## Similarity dimensions

Every dimension contributes to the overall score (weights sum to 1.0):

| Dimension | Weight | Primary tip |
|---|---|---|
| Interest-rate regime | 0.16 | Repo Rate |
| Inflation regime | 0.14 | CPI |
| GDP regime | 0.14 | GDP |
| Liquidity regime | 0.12 | Banking Liquidity |
| Fiscal regime | 0.10 | Fiscal Deficit |
| Currency regime | 0.10 | USDINR |
| Bond yield regime | 0.08 | G-Sec 10Y |
| Global growth regime | 0.10 | WEO Global Growth |
| Commodity regime | 0.06 | WPI |

Method: weighted relative distance. Match threshold: 70. No analogue without explainability bundle.

---

## APIs

```text
GET  /v1/macro/analogues
GET  /v1/macro/analogues/{country}
GET  /v1/macro/analogues/search
GET  /v1/macro/regime/current
GET  /v1/macro/regime/history
POST /v1/macro/analogues/run
GET  /v1/hmai/health
GET  /v1/admin/macro-analogues
```

Read paths never collect. `POST .../run` is ops/scheduler only.

---

## Traces

`macro_analogue_search` · `macro_similarity_scoring` · `macro_analogue_ranking` · `macro_analogue_retrieval`

---

## Mission Control

**Historical Macro Analogue** board:

- Current macro regime
- Top analogue matches
- Similarity distribution
- Confidence
- Historical coverage
- Analogue freshness

---

## Forecast consumption

IFI soft-consumes `forecast_tip()` with `providers_queried: []`. Sprint 10.5 Macro Forecast Intelligence will reason from these analogue bundles without external API calls.

---

## Phase 10 progress

| Sprint | Module | Status |
|---|---|---|
| ✅ 10.1 | CMKP | Continuous ingestion |
| ✅ 10.2 | HMIP | Historical memory |
| ✅ 10.3 | MRI | Relationships |
| ✅ 10.4 | HMAI | Analogues |
| ✅ 10.5 | MFI | Macro forecast scenarios |
