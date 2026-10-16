# Sprint 6.4 — Knowledge Retrieval & Intelligence Gateway (KRIG)

## Mission

Turn AGI's continuously learned knowledge into something the Intelligence Engine can retrieve in milliseconds.

```text
Ask → KRIG → Knowledge Bundle → Reason
```

IE performs **zero data discovery**. It never sees Yahoo / NSE / BSE.

## Contract

`knowledge-platform/docs/KRIG_PLATFORM_CONTRACT.md`

## What shipped

- Retrieval policies (company / sector / macro / market / portfolio / compare)
- Knowledge Bundle standard object + checklist
- Freshness Engine (per-section SLA)
- Bundle cache (TTL)
- Gateway APIs: `/v1/knowledge/bundle`, `/compare`, `/macro`, `/market`, …
- Storage: `knowledge_bundle_cache`, `retrieval_logs`, `freshness_registry`, `knowledge_dependencies`, `retrieval_metrics`
- IE `KrigClient` + Ask soft-wire (`SearchView.knowledge_bundle`)

## Success path

`Compare HDFC Bank vs ICICI Bank after RBI cut rates` → Comparison Bundle with both companies, banking sector tip, RBI macro / historical cycle, learning, valuation, evidence links.

## Verification

```bash
cd knowledge-platform && pytest -q
```

## Next

Sprint 6.5 — Knowledge Operations (KOps): source health, freshness ops, retries/DLQ, quality scoring, provenance dashboards.
