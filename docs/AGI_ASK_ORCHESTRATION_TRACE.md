# Ask orchestration trace (observability)

Extends PR #434 with per-request telemetry so founder debugging does not rely on inference.

## Shape (`ask_orchestration`)

Returned on every Ask response (engine success, Node fallback, and exception degrade):

```json
{
  "version": "ask-orchestration-trace-1",
  "entity": {
    "detected": "META",
    "aliases_matched": ["META", "Meta Platforms"],
    "confidence": 0.99,
    "source": "alias_override",
    "needs_clarification": false,
    "low_confidence": false
  },
  "funnel": {
    "retrieved": 14,
    "ranked": 6,
    "passed_to_ice": 5,
    "referenced": 4,
    "utilization": 0.8,
    "zero_stage": null
  },
  "latency_ms": {
    "entity_resolution": 12,
    "retrieval": 8200,
    "reasoning": 11000,
    "response_assembly": 400,
    "total": 23600
  },
  "executive_attribution": [
    {"paragraph": 1, "evidence_title": "Meta Q2 earnings", "grounded": true}
  ],
  "executive_overwritten": false,
  "fallback": false,
  "grounding": 1.0,
  "trace_summary": "Entity: META (0.99) | Retrieved: 14 → …"
}
```

Also mirrored under `degradation.ask_orchestration` and `answer.ask_orchestration`.

## What we had before vs now

| Capability | Before (#434) | Now |
|------------|---------------|-----|
| Fallback / engine_reached | partial | yes |
| Ticker source / rejects | yes | yes |
| Retrieval funnel | no | yes |
| Utilization (referenced ÷ passed) | no | yes |
| Latency by stage | no | yes |
| Entity confidence | no | yes |
| Executive attribution | no | yes (best-effort) |

## Verify

```bash
cd intelligence-engine
pytest tests/test_ask_orchestration_trace.py tests/test_ask_orchestration_guards.py -q
```
