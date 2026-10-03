# Phase X — AGI Ask Evidence Intelligence & Observability

Foundation for founder debugging **before** latency optimization or corpus expansion.

## Status vs prior PRs

| Capability | #434 | #435 | This PR |
|------------|------|------|---------|
| Honest fallback / ticker guard / ICE executive | ✓ | | |
| Funnel Retrieved→Ranked→Passed→Referenced | | ✓ | ✓ |
| Utilization | | ✓ | ✓ |
| Efficiency + Precision | | | ✓ |
| Stage latency (entity/retrieval/ranking/reasoning/assembly/serialization/http) | | partial | ✓ |
| Entity confidence + rejected candidates | | partial | ✓ |
| Executive attribution | | ✓ | ✓ |
| `ask_trace_id` end-to-end | | | ✓ |
| Mission Control dashboard | | | ✓ |
| In-process KPI ring buffer | | | ✓ |

## Response diagnostics (`ask_orchestration`)

Internal only (`diagnostics_visibility: "internal"`). Not product copy for end users.

```json
{
  "ask_trace_id": "ASK-20260801-92F31A",
  "engine_reached": true,
  "fallback_used": false,
  "entity": {
    "name": "Meta Platforms",
    "confidence": 0.99,
    "aliases_matched": ["META", "Meta Platforms"],
    "rejected_candidates": ["SUMMARIZE", "JSWSTEEL"],
    "resolution_source": "alias_override"
  },
  "evidence": {
    "retrieved": 18,
    "ranked": 7,
    "passed": 5,
    "referenced": 4,
    "utilization": 0.8,
    "efficiency": 0.22,
    "precision": 0.57
  },
  "latency": {
    "entity_ms": 18,
    "retrieval_ms": 420,
    "ranking_ms": 180,
    "reasoning_ms": 7100,
    "assembly_ms": 70,
    "serialization_ms": 5,
    "http_ms": 7790,
    "total_ms": 7790
  },
  "executive_attribution": [],
  "trace_summary": "…"
}
```

Also: `X-Ask-Trace-Id` response header (Node gateway). Gateway `ask_trace_id` is
propagated into the engine via body + header so ingress→completion share one id.

## Progressive stage checkpoints (hang diagnosis)

Every Ask marks stages and flushes a **partial** trace after each mark:

`http_ingress → entity_resolution → ikl → retrieval → ranking → reasoning → response_assembly → serialization → http`

Threshold warnings (log only — no timeout changes):

| Stage | Threshold |
|-------|-----------|
| Entity | 250ms |
| IKL | 500ms |
| Retrieval | 2s |
| Ranking | 1s |
| Reasoning | 20s (+ extra warn at 30s with docs/model/latency) |
| Assembly | 2s |

On gateway timeout, Node returns fallback with:

`completed=false`, `timeout=true`, `last_completed_stage`, `elapsed_ms`, `ask_trace_id`, `execution_trace`.

## Baseline runner (always writes)

```bash
cd intelligence-engine
ASK_TEST_MODE=live \
ASK_TEST_BASE=https://finance-news-backend-19i5.onrender.com \
  python3 -m ask_product_test.run_baseline
```

- Writes `artifacts/ask_test_report_pre_ikl_<UTC>.json` after **every** prompt
- Never overwrites prior stamped reports
- Exits cleanly even when Ask times out
- Prints founder execution traces per question

## Mission Control

- API: `GET /v1/mission-control/ask-observability`
- Node: `GET /api/intelligence/mission-control/ask-observability`
- UI: Admin → Mission Control → **Ask Observability** panel

## Verify

```bash
cd intelligence-engine
pytest tests/test_ask_orchestration_stages.py tests/test_ask_orchestration_trace.py tests/test_ask_observability_store.py -q
```
