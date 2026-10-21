# AGI IHG Evaluation — Phase 4 Sprint 4.2

```text
COMPANY: AGI
SPRINT: Phase 4 · Sprint 4.2 Institutional Hypothesis Generation
IHG: institutional-hypothesis-generation-v1.0.0
CATALOG: ihg-hypothesis-catalog-v1.0.0
IEW: institutional-evidence-weighting-v1.0.0
DATE: 2026-07-28
```

## Method

- Soft-wire IHG after IEW in Ask pipeline + IEL soft probe.
- Run `institutional_1000` + `cio_frozen_25` (soft).
- Compare to AGI v3.5 CERTIFIED baseline and IEW v1.0.0 soft results.
- Unit suite validates determinism, conflict retention, no fabrication, plural outcomes.

## Results

| Metric | Frozen v3.5 | IEW soft | IHG soft |
|--------|------------:|---------:|---------:|
| IEL 1000 pass % | 99.9 | 99.9 | **99.9** |
| IEL mean | 90.24 | 90.05 | 90.05 |
| CIO-25 pass % | 100 | 100 | **100** |
| Reasoning changed | No | No | **No** |
| Forced single winner | — | — | **No** |

Regression gate: `regression=false`.

## Smoke (live Ask)

Question: *Why did Infosys margins decline after cost inflation?*

- Outcome: `preferred`
- Winning hypothesis: input-cost inflation (`HYP-margin_decline-input_cost_inflation-…`)
- `plural: true` (other hypotheses retained with shares)

## Exit gate

| Gate | Status |
|------|--------|
| Deterministic hypothesis generation | ✓ |
| Replay / TIRC / IEW preserved | ✓ |
| No reasoning / framework / communication regression | ✓ |
| LangSmith spans complete | ✓ instrumented |
| Hypothesis explanations | ✓ |
| IEL stable | ✓ 99.9% |
| CIO held | ✓ 100% |
| No forced single winner | ✓ |

## Next

Sprint 4.3 Contradiction Resolution operates on contested / conflicting hypotheses.
