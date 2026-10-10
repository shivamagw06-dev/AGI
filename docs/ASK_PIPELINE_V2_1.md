# AGIB v2.1 Track 1 — Complete Ask Pipeline

**Integration only.** Phase 1–7, Knowledge Factory, governance, committees, evidence contracts, DQ scoring, and CAL are frozen.

## Contract

See [`ASK_PIPELINE_RUNTIME_DEPENDENCY_MAP.md`](./ASK_PIPELINE_RUNTIME_DEPENDENCY_MAP.md) — required before / with this implementation.

## Package

`intelligence-engine/ask_pipeline/`

| Module | Stage |
| --- | --- |
| `context.py` | AskContext |
| `intent.py` | Intent detection |
| `entities.py` | Multi-entity resolution |
| `knowledge.py` | KF-primary selective retrieval |
| `evidence.py` | Evidence pack assembly |
| `planner.py` | Existing IRO `plan_research` |
| `dag.py` | Integration DAG record |
| `pipeline.py` | `run_complete_ask` |
| `recording.py` | DQ record + IOI register |
| `telemetry.py` / `gates.py` / `dashboard.py` | Observability |

## Soft-wires

- `UiService.search` → `run_complete_ask` (replaces bare `govern_answer` call; still invokes existing `govern_answer` inside)
- Read APIs: `/v1/ask/pipeline`, `/context`, `/execution`, `/telemetry`, `/replay`, `/quality-gates`

## Tests

`intelligence-engine/tests/test_ask_pipeline.py`
