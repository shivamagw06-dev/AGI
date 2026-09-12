# AGI Engineering Baseline — FROZEN (v3.5)

```text
COMPANY: AGI
ENGINEERING BASELINE FROZEN: YES
BOARD VERDICT: CERTIFIED
DATE: 2026-07-28
SPRINT LOCK: post Framework Opt + Intent Opt + TIRC
```

## Frozen reference metrics (full path, 1,025)

| Metric | Frozen value |
|--------|-------------:|
| IEL pass | **99.9%** |
| Mean score | 90.24 |
| Intent | 99.8% |
| Framework | 97.76% |
| Playbook | 99.61% |
| Evidence graph hit | 100% |
| Historical replay accuracy | **100%** |
| Future leakage | **0** |
| Hallucinated evidence | 0 |
| CIO-25 pass | **100%** |

## Institutional guarantees

1. **Temporal integrity** — Replay Guard enforces `available_from <= as_of` and rejects future-year surfaces/analogs.
2. **Routing quality** — Intent/framework optimisation held (portfolio intent clusters cleared).
3. **Evaluation loop** — IEL → RCI → Patch Intelligence → human review.

## Rule for future PRs

Every change must beat or hold these frozen metrics. Regressions on replay integrity or future leakage are release blockers.
