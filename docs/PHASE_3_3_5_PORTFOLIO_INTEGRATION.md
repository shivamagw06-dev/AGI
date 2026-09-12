# Phase 3.3.5 — Portfolio Intelligence KUL Integration

## Status

- Engine Acceptance: 300Q
- KUL provider: `portfolio_intelligence` (foundation)
- `ASK_WIRED = True` via KUL only
- Integration Acceptance: 75 questions · gate ≥90%

## Commands

```bash
cd intelligence-engine
PYTHONPATH=. python3 ask_product_test/run_pi_integration_acceptance_v1.py
```

## Non-goals

- No Core modifications
- No BUY/SELL / trade recommendations
- Soft-slice is diagnostics only — production Ask uses KUL
