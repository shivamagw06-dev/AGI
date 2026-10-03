# AGI — LangSmith Tracing (langsmith-trace skill)

**Package:** `intelligence-engine/observability/`  
**Version:** `agi-observability-v1.0.0`  
**Skills installed from:** https://github.com/langchain-ai/langsmith-skills → `.claude/skills/{langsmith-trace,langsmith-dataset,langsmith-evaluator}`

AGI is not a LangChain/LangGraph app, so per the `langsmith-trace` skill this uses the **manual instrumentation path**: `traceable`-style spans around pipeline stages plus `run_type="llm"` spans on the raw Gemini/OpenAI calls, and `wrap_openai()` on the OpenAI SDK client.

## Enable

```bash
export LANGSMITH_API_KEY=lsv2_pt_...        # required
export LANGSMITH_TRACING=true                # optional; defaults ON when key present
export LANGSMITH_PROJECT=agi-intelligence-engine   # optional
export LANGSMITH_WORKSPACE_ID=...            # optional (org-scoped keys)
```

With no key, tracing is a **no-op**: decorators return the original function and spans yield an inert handle. This is why the frozen v3.5 baseline is unaffected.

## Traced spans

Root: `agi.ask_pipeline` (`run_type=chain`), with children:

| Span | Run type |
|------|----------|
| `intent_resolution` | chain |
| `knowledge_retrieval` | retriever |
| `evidence_assembly` | retriever |
| `framework_selection` | chain |
| `playbook_selection` | chain |
| `evidence_graph` | retriever |
| `temporal_integrity.replay_guard.pre_analog` | chain |
| `institutional_analog_intelligence` | retriever |
| `temporal_integrity.replay_guard.post_analog` | chain |
| `reasoning.governance` | chain |
| `institutional_communication` | chain |
| `gemini:<model>` (editorial writer + CIO synthesis) | llm |
| OpenAI SDK calls via `wrap_openai` | llm |

Frozen modules (reasoning, Knowledge Factory, framework selector, intent resolver, playbooks) are **not edited** — the Ask pipeline wraps their call sites instead.

## Safety properties

- **Fail-open:** every tracing path is wrapped in `try/except`; a broken or missing SDK cannot fail a request. Covered by `test_tracing_failure_does_not_break_caller`.
- **Output-neutral:** verified by re-running the full 1,025-question IEL with tracing off — **zero drift** (pass 99.9%, intent 99.8%, framework 97.76%, replay 100%, future leakage 0, CIO-25 100%).
- **Exceptions preserved:** decorators re-raise the original error unchanged.
- **Bounded payloads:** inputs/outputs are projected to JSON-ish values, truncated at 4,000 chars and 40 items per collection.

## APIs

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/observability/health` | tracing state + required env |
| `GET /v1/observability/langsmith` | dashboard: project, endpoint, traced stages, CLI hint |
| `GET /v1/observability/langsmith/verify` | emit one synthetic trace (`agi.observability.verify`) |

Mission Control exposes an `observability` block (provider, enabled, project, traced stage count).

## Querying traces

```bash
langsmith trace list --project agi-intelligence-engine --limit 10 --api-key $LANGSMITH_API_KEY
langsmith trace list --error --last-n-minutes 60 --api-key $LANGSMITH_API_KEY
langsmith trace list --min-latency 5 --include-metadata --api-key $LANGSMITH_API_KEY
langsmith trace export /tmp/traces --limit 20 --full --api-key $LANGSMITH_API_KEY
```

## Render deployment

The key belongs to the **`agib-intelligence-engine`** service (Python) — that is where the tracing code lives. Setting it on `agib-api` (Node) has no effect, because the Node LLM client (`server/services/llmClient.js`) is not instrumented.

`render.yaml` now declares for that service:

| Key | Source |
|-----|--------|
| `LANGSMITH_API_KEY` | `sync: false` → set in Render dashboard |
| `LANGSMITH_TRACING` | `"true"` |
| `LANGSMITH_PROJECT` | `agi-intelligence-engine` |
| `LANGSMITH_WORKSPACE_ID` | `sync: false` (org-scoped keys only) |

`langsmith` is in `requirements.txt`, and the service `buildCommand` already runs `pip install -r requirements.txt`, so a redeploy installs the SDK.

**Tracing only begins once this branch is merged and deployed.** As of this commit the live engine still runs an older revision — `/v1/observability/health` and `/v1/temporal-integrity/health` both return 404 there, while `/v1/health` returns 200.

Confirm after deploy:

```bash
curl -s https://agib-intelligence-engine.onrender.com/v1/observability/health | jq .tracing_state
# expect: "tracing"
curl -s https://agib-intelligence-engine.onrender.com/v1/observability/langsmith/verify
# emits run "agi.observability.verify"
```

## Verification performed

A local fake ingest endpoint (`LANGSMITH_ENDPOINT=http://127.0.0.1:8124`) captured a real Ask run and confirmed 13 distinct run names posted to `/runs/multipart`, including `agi.ask_pipeline`, both replay-guard spans, and every stage above.
