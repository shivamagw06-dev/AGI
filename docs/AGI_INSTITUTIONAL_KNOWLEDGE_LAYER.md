# Institutional Knowledge Intelligence Layer (IKL)

## Mission

Transform AGI from query-time document retrieval into a continuously learning institutional research platform.

Every ingested document updates persistent institutional knowledge **before** any user asks a question.

> Never a second knowledge system — IKL is a façade over CID, Company Memory, KF/KC, KIL, and the Knowledge Graph.

## Pipeline

```text
Gather
  ↓
Documents
  ↓
Embeddings
  ↓
Knowledge Extraction   ← Universal Knowledge Extractor
  ↓
Entity Memory          ← Company / Industry / Macro (incremental)
  ↓
Knowledge Graph        ← confidence-weighted relationships
  ↓
Ask AGI                ← memory before raw documents
```

## Package

`intelligence-engine/institutional_knowledge_layer/`

| Module | Role |
|--------|------|
| `extractor.py` | Structured slots from any document type |
| `memory/company.py` | Incremental company profile |
| `memory/industry.py` | Incremental industry memory |
| `memory/macro.py` | Macro topics + industry spillover |
| `graph.py` | Relationship edges + adjacency index |
| `deltas.py` | Cross-document meaningful changes only |
| `writeback.py` | Continuous learning on ingest / CGL |
| `consult.py` | Ask retrieval order + explainability bag |
| `production.py` | Soft façade (never raises) |
| `flags.py` | `IKL_*` env toggles |

## Ask retrieval order

1. Company Memory  
2. Industry Memory  
3. Macro Memory  
4. Knowledge Graph  
5. Structured KPIs  
6. Historical Timeline  
7. Raw Documents  
8. Live Search (only if required)

## Soft-wire

| Surface | Hook |
|---------|------|
| KIP ingest | `_kf_soft_learn` → `ikl.on_document` |
| Continuous Gather → Learn | after KIL → `ikl.after_cgl_cycle` |
| Ask desk (`UiService.search`) | after CID → `ikl.ask_consult` → `institutional_knowledge` + `ask_orchestration.ikl` |
| Ask pipeline | `ask_pipeline/knowledge.py` prepends IKL pack |

## APIs

- `GET /v1/ikl/health`
- `GET /v1/ikl/memory/{ticker}`
- `POST /v1/ikl/learn`

## Flags

| Env | Default | Meaning |
|-----|---------|---------|
| `IKL_ENABLED` | `1` | Master switch |
| `IKL_WRITEBACK_ENABLED` | `1` | Learn on ingest |
| `IKL_ASK_CONSULT_ENABLED` | `1` | Consult on Ask |
| `IKL_DELTA_ENABLED` | `1` | Cross-document deltas |

## Explainability (internal)

`ask_orchestration.ikl.explainability` and `institutional_knowledge.explainability` expose:

- knowledge sources / layers hit  
- company / industry / macro memory used  
- documents referenced  
- reasoning path  
- knowledge gaps  
- confidence  

Never exposed as end-user implementation detail.

## Acceptance

- A newly ingested document updates IKL memories without a user query.  
- Ask reasons primarily from structured institutional memory; raw documents support.  
- No unsupported investment recommendations — evidence-grounded only.  
- Memories update incrementally (never full rebuild on each document).

## Founder validation suite (Tier IKL)

Five prompts in `ask_product_test/prompts.py` → `IKL_PROMPTS`, run via:

```bash
cd intelligence-engine
pytest tests/test_ask_product_ikl.py -q

# After deploy — require memory layers
ASK_TEST_MODE=live ASK_TEST_IKL_STRICT=1 \
  pytest tests/test_ask_product_ikl.py -q
```

| ID | Question focus | Expected layers |
|----|----------------|-----------------|
| IKL-01 | Reliance business model | `company_memory` first |
| IKL-02 | Meta AI infra evolution | timeline / multi-doc |
| IKL-03 | Hospitals vs pharma valuation | `industry_memory` |
| IKL-04 | Crude ↓ → aviation / paints / OMCs | `macro_memory` + graph |
| IKL-05 | XYZ Private Ltd | knowledge gap, no hallucination |

Compare live Tier A/B reports via `comparison_metrics` before vs after deploy
(`artifacts/ask_test_report_pre_ikl.json` → post-deploy `ask_test_report.json`).
