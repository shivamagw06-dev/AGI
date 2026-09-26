# KG-01 — Institutional Knowledge Graph

**Mission:** AGI stores **connected institutional knowledge**, not isolated facts. Every recommendation, confidence score, reason, and report must be traceable through the graph.

```text
Evidence → Knowledge Graph → Inference → Reasons → Decision → Calibration → Report
```

**Scope (this sprint):** single company only.  
One company → its evidence → metrics → risks → valuation → reasons → decision → calibration.

No Gemini. No GPT. No phrase bank. No cross-company / portfolio / market graphs yet.

## Model

- **Entity** — `id`, `type`, `version`, `timestamp`, `source`, `confidence`, provenance, impact
- **Relationship** — direction/kind, strength, evidence, confidence, version
- Node types include Company, Sector, FinancialMetric, MacroVariable, ValuationMetric, Risk, Catalyst, Forecast, Reason, Decision, Evidence, Calibration

## Engines

| Module | Role |
| --- | --- |
| `graph.py` | Build single-company graph from report input + reasons + decision |
| `inference.py` | `infer(graph)` → derived relationships |
| `impact.py` | Impact scores on key nodes |
| `traversal.py` | `path_between`, `shortest_reason_path`, `evidence_chain`, `decision_chain`, `impact_chain` |
| `diagnostics.py` | Size, coverage, cycles, quality gates |

## Access

```bash
cd intelligence-engine
PYTHONPATH=. python3 -m institutional_graph --ticker AXISBANK
PYTHONPATH=. python3 -m institutional_graph --ticker AXISBANK --include-paths
```

API:

- `GET /v1/graph/health`
- `GET /v1/graph/company/{ticker}?include_paths=true&include_inference=true`
- `POST /v1/graph/company`

BFF: `/api/intelligence/graph/*`

## UI

Company workspace → **Knowledge Graph** tab: entities, relationships, impact, clickable nodes, decision path.

## Mission Control

Knowledge Health soft slice: graph coverage, disconnected nodes, inference quality, average path length, entity/relationship counts.

## Out of scope

Phrase bank, LLM, market graph, portfolio graph, cross-company graph.
