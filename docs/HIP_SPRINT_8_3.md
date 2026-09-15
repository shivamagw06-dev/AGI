# Phase 8 — Sprint 8.3: Historical Relationship Intelligence (HRI)

**Status:** Implemented in `historical-platform/` (HIP v0.3.0)  
**Depends on:** Sprint 8.2 HKO + Timeline Intelligence  
**Out of scope:** Pattern & cycle detection (8.4), historical analogues (8.5)

---

## Why HRI before patterns

Institutional analysts learn **cause and effect** before they recognise recurring patterns.

```text
RBI Rate Cut
  → Lower borrowing costs
  → Bank lending improves
  → Private Banks outperform
  → Housing demand increases
  → Auto financing improves
  → HDFC Bank (Positive Historical Impact)
```

That transmission chain is reusable institutional knowledge — not a generic pattern score.

---

## Delivered

| Capability | Location |
|---|---|
| Evidence-backed relationship catalog | `app/hri/catalog.py` |
| Relationship engine + validation + publication | `app/hri/engine.py`, `validation.py` |
| Graph storage | `historical_relationships` + domain indexes + evidence + versions |
| APIs | `/v1/history/relationships/*` + `/explain` |
| Mission Control relationship board | `/v1/history/mission-control` |
| KRIG soft bridge | `knowledge-platform/app/krig/historical_bridge.py` |
| Traces | `historical_relationship_builder`, `relationship_validation`, `relationship_publication`, `relationship_retrieval` |

---

## Success path

```bash
curl -X POST http://127.0.0.1:8092/v1/internal/bootstrap
curl http://127.0.0.1:8092/v1/history/relationships/company/INFY
curl http://127.0.0.1:8092/v1/history/relationships/macro/rbi_rate_cut
curl -X POST http://127.0.0.1:8092/v1/history/relationships/explain \
  -H 'content-type: application/json' \
  -d '{"source":"RBI Rate Cut","target":"HDFCBANK"}'
```

All responses include `providers_queried: []`.

---

## Roadmap

| Sprint | Module | Purpose |
|---|---|---|
| ✅ 8.1 | HAP | Historical data ingestion |
| ✅ 8.2 | HKO + Timeline | Structured historical memory |
| ✅ 8.3 | HRI | Cause-and-effect relationships |
| 8.4 | HPCI | Recurring patterns & cycles |
| 8.5 | HAI | Historical analogues for today |
