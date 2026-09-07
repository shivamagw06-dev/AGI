# Phase 3.4.5 — Research Intelligence KUL Integration

## Status

- Engine Acceptance v1.0: 400Q gate (≥95%, hard zeros)
- KUL provider: `research_intelligence`
- `ASK_WIRED = True` via KUL only (no Ask bypass)
- Integration Acceptance: 100 questions · gate ≥90%

## Ask path

```
Question → Knowledge Planner
  → Research Intelligence (research-shaped)
  → Investment / BI / Industry / CapIQ / memory / KF
  → Evidence Fusion → Executive Composer
```

## Commands

```bash
cd intelligence-engine
PYTHONPATH=. python3 ask_product_test/run_ri_integration_acceptance_v1.py
PYTHONPATH=. python3 ask_product_test/run_research_intelligence_acceptance_v1.py
PYTHONPATH=. python3 ask_product_test/run_research_golden_25.py
```

## Non-goals

- No Core modifications
- No BUY/SELL / forecasts as answers
- Soft-slice is diagnostics only — production Ask uses KUL
