# Phase 3.4 — Research Intelligence Engine

**Status:** Build complete · Acceptance Test v1.0 formalized · Ask/KUL **not wired**  
**Depends on:** AGI Core v1.1 (extend only) + Investment Intelligence + Portfolio Intelligence  
**Version:** `3.4.0`

## Discipline

```
Build → Acceptance Test → Integration → Production Validation → Freeze
```

This branch lands the **permanent Research Intelligence Acceptance Test v1.0** and three regression suites. KUL integration remains deferred.

## Acceptance gate (v1.0)

| Metric | Threshold |
|--------|-----------|
| Questions | 400 (sections A–K) |
| Pass rate | ≥95% |
| Hallucinations | 0 |
| Recommendation leakage | 0 |
| Research memory leakage | 0 |
| Planner accuracy | 100% |
| `ASK_WIRED` | `False` |

```bash
cd intelligence-engine
PYTHONPATH=. python3 ask_product_test/run_research_intelligence_acceptance_v1.py
PYTHONPATH=. python3 ask_product_test/run_research_golden_25.py
PYTHONPATH=. python3 ask_product_test/run_research_timeline_regression.py
PYTHONPATH=. python3 ask_product_test/run_research_memory_regression.py
```

## Knowledge authority

**Research Intelligence is the only Phase-3 layer allowed to create new long-lived research knowledge.**  
Financial / Business / Industry / Investment / Portfolio layers **consume** structured research outputs.

## Explicit non-goals (this PR)

- No KUL provider registration
- No Ask wiring (`ASK_WIRED = False`)
- No BUY/SELL / forecasting as answers (Section K refusals)
- No Core modifications

## Next

1. Register `research_intelligence` in KUL  
2. Research Integration Acceptance (~100)  
3. Founder Evaluation V6  
4. Production validation (full gate including Research Acceptance + regressions) → Freeze  
