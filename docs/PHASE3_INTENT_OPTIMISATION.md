# Phase 3 Sprint 3.4 — Intent Optimisation

## Scope

Optimise existing Intent Resolution Layer using **RCI failure clusters only**.

Do **not**:

- Create another intent engine
- Add intent categories
- Redesign routing / reasoning / frameworks / playbooks / Knowledge Factory

## Input

- Root Cause Intelligence clusters (post Framework Optimisation)
- IEL institutional_1000 failures
- Patch Intelligence recommendations

## Target clusters

1. Portfolio intent  
2. Allocation intent  
3. Rebalancing intent  
4. Sector allocation  
5. Portfolio risk review  
6. Watchlist intent  
7. Investment committee requests  

## Approach

Improve cue detection, confidence, priority, conflict resolution, and disambiguation inside `ask_pipeline/intent_resolution/` — especially Education vs Portfolio Review vs Construction vs Allocation vs Rebalancing vs Risk Review vs IC.

## Soft-wire order (unchanged)

```text
Intent → Evidence → Assembly → Framework → Playbook → Evidence Graph → IMAI → Reasoning → ICE
```

## Exit metrics

| Metric | Target | Observed (soft) |
|--------|-------:|----------------:|
| Intent accuracy | ≥99% | 100.0% |
| Framework accuracy | ≥96% | 97.7% |
| IEL pass | ≥95% | 98.4% |

See `docs/AGIB_IO_BASELINE_REPORT.md`.
