# Phase 3.2.5 — Investment Intelligence Integration

Wire Investment Intelligence into the Knowledge Unification Layer without changing AGI Core contracts.

## Status

- Engine Acceptance (3.2): 300/300
- KUL provider: `investment_intelligence`
- Ask: via KUL only (`ASK_WIRED=True`)
- Integration Acceptance: 75 live questions (gate ≥90%, freeze targets 100%)
- Founder Evaluation V4: 100 questions (gate ≥95%)

## Architecture

```
Question → Knowledge Planner → Investment Intelligence → Industry Intelligence
         → Business Intelligence → Financial Intelligence → CapIQ → IKL
         → Company Memory → Knowledge Factory → Continuous Gather
         → Evidence Fusion → Executive Composer
```

## Planner activation

Investment Intelligence activates for thesis, quality, capital allocation, catalysts, risks, scenarios, valuation interpretation, evidence strength, monitoring, investment comparisons, and Evaluate/Assess/Analyze + company questions.

Industry pedagogy (e.g. “Why do banks use P/B?”) still leads with Industry Intelligence.

## Recommendation policy

Observations only — no BUY / no SELL / no target prices.

## Commands

```bash
cd intelligence-engine
PYTHONPATH=. python3 ask_product_test/run_inv_integration_acceptance_v1.py
PYTHONPATH=. python3 ask_product_test/run_founder_evaluation_v4.py
```

See also: `docs/KNOWLEDGE_DEPENDENCY_MAP.md`, `investment_intelligence/PHASE32_05_NOTES.md`
