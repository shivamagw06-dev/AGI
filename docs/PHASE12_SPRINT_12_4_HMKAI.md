# Phase 12 — Sprint 12.4: Historical Market Analogue Intelligence (HMKAI)

**Status:** Implemented in `intelligence-engine/historical_market_analogue_intelligence/`  
**Version:** 0.1.0  
**Pattern:** Market twin of HSAI / Macro HMAI  
**Note:** Programme short is **HMKAI** to avoid collision with Historical Macro Analogue Intelligence (**HMAI**).

---

## Objective

Identify and rank historical market environments most similar to the current market using deterministic, evidence-backed similarity analysis across regime, breadth, liquidity, volatility, flows, leadership and macro context.

Every analogue is explainable, versioned and traceable — ready for Market Forecast Intelligence (12.5).

---

## Architecture

```text
CMKTP · HMKIP · MKRI · HMIP · HSIP · Research
                │
                ▼
Market Analogue Engine → Similarity → Ranking
                │
Historical Market Analogues → HMKAI_KRIG → Market Forecast Intelligence
```

---

## Similarity dimensions

`market_regime` · `breadth` · `liquidity` · `volatility` · `fii_flows` · `dii_flows` · `leadership` · `bond_yields` · `usd_index` · `interest_rate` · `inflation`

Weights sum to 1.0. Scoring uses weighted relative distance and is fully deterministic / reproducible.

---

## Guardrails

* Ask never rebuilds catalogues
* `providers_queried` always `[]` on read paths
* Soft-consumes CMKTP / HMKIP / MKRI / HMIP tips during enrichment only
* No BUY/SELL, targets, or single-path forecasts (deferred to 12.5)

---

## APIs

| Method | Path | Notes |
|---|---|---|
| GET | `/v1/hmkai/health` | Programme health |
| GET | `/v1/market/analogues` | Ranked analogues |
| GET | `/v1/market/analogues/{market}` | Per-market surface |
| GET | `/v1/market/analogues/search` | NL / period filters |
| GET | `/v1/market/analogues/report` | Institutional report |
| GET | `/v1/market/analogues/dashboard` | Mission Control JSON |
| POST | `/v1/market/analogues/run` | Ops rebuild only |
| GET | `/v1/market/regime/current` | Current regime vector |
| GET | `/v1/market/regime/history` | Historical regime catalog |
| GET | `/v1/admin/historical-market-analogues` | HTML ops board |

---

## LangSmith traces

```text
market_analogue_search
market_similarity_scoring
market_analogue_ranking
market_analogue_retrieval
market_analogue_refresh
```

---

## Mission Control

**Historical Market Analogue** board (`phase: 12.4`):

* Current market regime · Top matches · Similarity / confidence distribution · Matching dimensions · Key differences · Historical outcomes · Coverage · Freshness

---

## Soft consumers

* **IFI** soft-reads HMKAI via `forecast_tip` / `HMKAI_KRIG`
* Forecast sprint 12.5 will consume analogue bundles without external providers

---

## Phase 12 roadmap

| Sprint | Module | Status |
|---|---|---|
| ✅ 12.1 | CMKTP — Continuous Market Knowledge | Complete |
| ✅ 12.2 | HMKIP — Historical Market Intelligence | Complete |
| ✅ 12.3 | MKRI — Market Relationship Intelligence | Complete |
| ✅ 12.4 | HMKAI — Historical Market Analogue Intelligence | Complete |
| ✅ 12.5 | MKFI — Market Forecast Intelligence | Complete |
