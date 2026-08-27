# AGIB v3.4 Track B — Institutional Answer Assembly Engine

## Goal

Turn retrieved evidence into a **planned institutional answer** before narrative writing.

Not:

```text
Evidence → LLM → Answer
```

Instead:

```text
Evidence Pack
  → Evidence Classification
  → Framework Inputs / Importance Ordering
  → Gap Detection
  → Answer Skeleton
  → Confidence Calibration
  → Citation Mapping
  → Existing Reasoning (bind)
  → Editorial (Track D)
```

## Stages

| Stage | Module | Purpose |
|-------|--------|---------|
| 1 | `classify.py` | Map IERE / packs → Financial, Accounting, Macro, Documents, … |
| 2 | `ordering.py` | Intent-aware domain priority (e.g. banks P/B: Accounting → Business Model → Framework → Historical before Macro) |
| 3 | `gaps.py` | Missing domains → tell reasoning; confidence penalty |
| 4 | `skeleton.py` | Fixed sections: exec summary → evidence → analysis → framework → risks → conclusion → confidence → sources |
| 5 | `confidence.py` | Deterministic High / Moderate / Low / Insufficient |
| 6 | `citations.py` | Section → evidence IDs → documents / objects / replay |

## Soft-wires

- `ask_pipeline/answer_assembly/` — new engine
- `ask_pipeline/pipeline.py` — assemble after S06 evidence; bind after S09 governance
- `ask_pipeline/knowledge.py` — pass `ranked_evidence` for assembly (structured only)

Knowledge Factory, committees, and governance internals remain frozen. No LLM ranking or synthesis.

## Pipeline fields

- `answer_assembly` — full plan (classification, gaps, skeleton, citations, metrics)
- `institutional_answer` — skeleton filled from existing reasoning (no invented facts)
- `answer_assembly_version` — `answer-assembly-v1.0.0`
- `llm_synthesis_used: false`

## Exit discipline

Re-run the same 25-question CIO benchmark after merge. Merge only if overall score improves or stays neutral without regressions. Track C (framework selector) and Track D (narrative) come next — not in this PR.
