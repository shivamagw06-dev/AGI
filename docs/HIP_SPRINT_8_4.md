# Phase 8 — Sprint 8.4: Historical Analogue Intelligence (HAI)

**Status:** Implemented in `historical-platform/` (HIP v0.4.0)  
**Depends on:** Sprint 8.3 HRI  
**Out of scope:** Pattern & Cycle Intelligence (8.5), forecasting

---

## Objective

Answer **"Have we ever seen this before?"** with ranked, evidence-backed historical analogues — not forecasts.

---

## Delivered

| Capability | Location |
|---|---|
| Analogue Query Builder | `app/hai/query_builder.py` |
| Deterministic Similarity Engine | `app/hai/similarity.py` |
| Historical Analogue Engine | `app/hai/engine.py` |
| Search/result storage + Mission Control | `analogue_searches`, `analogue_results` |
| APIs | `/v1/history/analogues/*` |
| KRIG soft bridge | `search_analogues` on historical bridge |
| Traces | `historical_analogue_search`, `similarity_scoring`, `analogue_ranking`, `analogue_retrieval` |

---

## Success path

```bash
curl -X POST http://127.0.0.1:8092/v1/internal/bootstrap
curl -X POST http://127.0.0.1:8092/v1/history/analogues/search \
  -H 'content-type: application/json' \
  -d '{"scope":"company","entity":"INFY","question":"Has Infosys experienced this type of slowdown before?","top_k":5}'
```

Returns top analogues (e.g. FY2020 / FY2022 slowdown years) with similarity scores, matching dimensions, outcomes, timeline + relationship evidence, and `providers_queried: []`.

---

## Roadmap

| Sprint | Module | Purpose |
|---|---|---|
| ✅ 8.1 | HAP | Historical ingestion |
| ✅ 8.2 | HKO + Timeline | Structured historical memory |
| ✅ 8.3 | HRI | Cause-and-effect |
| ✅ 8.4 | HAI | Similar historical situations |
| ➡️ 8.5 | HPCI | Recurring patterns & cycles |
