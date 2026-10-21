# Phase 3.4 — Research Intelligence Engine

Transform AGI from answering questions into an **Institutional Research Platform**: create, maintain, and update structured research memory over time.

## Status

- **Build:** complete (`research_intelligence/`)
- **Acceptance:** Research Intelligence Acceptance Test v1.0 — 400 questions · gate ≥95% · hard zeros on hallucinations / reco / memory leakage · planner 100%
- **Regressions:** Research Golden 25 · Timeline Regression · Research Memory Regression
- **Ask / KUL:** `ASK_WIRED = False` until acceptance + integration gates
- **Core:** unchanged (extend only)
- **Depends on:** Investment Intelligence 3.2 · Portfolio Intelligence 3.3 · AGI Core v1.1

## Hierarchy

```
Financial Intelligence
        ↓
Business Intelligence
        ↓
Industry Intelligence
        ↓
Investment Intelligence
        ↓
Portfolio Intelligence
        ↓
Research Intelligence   ← Phase 3.4 (long-lived research memory authority)
```

## Knowledge authority

**Research Intelligence is the only Phase-3 layer allowed to create new long-lived research knowledge.**  
Other layers consume structured research outputs — they must not independently persist parallel research memories.

## REST

| Method | Path |
|--------|------|
| GET | `/v1/research-intelligence/health` |
| GET | `/v1/research-intelligence/dashboard` |
| GET | `/v1/research-intelligence/entities` |
| POST | `/v1/research-intelligence/analyse` |
| POST | `/v1/research-intelligence/soft_slice` |

## Executive research note order

1. Executive Summary  
2. What's New  
3. Business Impact  
4. Financial Impact  
5. Industry Impact  
6. Investment Implications  
7. Evidence  
8. Unknowns  
9. Monitoring Points  

## Acceptance & regressions

See [`PHASE_3_4_RESEARCH_ACCEPTANCE.md`](./PHASE_3_4_RESEARCH_ACCEPTANCE.md).

```bash
cd intelligence-engine
PYTHONPATH=. python3 ask_product_test/run_research_intelligence_acceptance_v1.py
PYTHONPATH=. python3 ask_product_test/run_research_golden_25.py
PYTHONPATH=. python3 ask_product_test/run_research_timeline_regression.py
PYTHONPATH=. python3 ask_product_test/run_research_memory_regression.py
```

## Deferred

1. KUL provider `research_intelligence`  
2. Research Integration Acceptance (~100)  
3. Founder Evaluation V6  
4. Production regression (including Research Acceptance + Golden 25 + Timeline + Memory) → Freeze  

See also: `docs/KNOWLEDGE_DEPENDENCY_MAP.md`
