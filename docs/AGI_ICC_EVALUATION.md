# AGI ICC Evaluation — Phase 4 Sprint 4.5

```text
COMPANY: AGI
SPRINT: Phase 4 · Sprint 4.5 Institutional Confidence Calibration
ICC: institutional-confidence-calibration-v1.0.0
CFQS: cfqs-v1.0.0
DATE: 2026-07-28
```

## Method

- Soft-wire ICC after frozen ICR in Ask pipeline + IEL soft probe.
- Run `institutional_1000` + `cio_frozen_25` (soft).
- Compare IEL / CIO / HQS / CQS to ICR baseline; introduce CFQS independently.
- Confidence is emergent from IEW→IHG→IHE→ICR — numeric + reason, never a bare label.

## Results

| Metric | ICR soft | ICC soft |
|--------|---------:|---------:|
| IEL 1000 pass % | 99.9 | **99.9** |
| IEL mean | 90.05 | **90.05** |
| CIO-25 pass % | 100 | **100** |
| HQS mean | 95.85 | **95.85** |
| CQS mean | 95.89 | **95.89** |
| **CFQS mean** | — | **100.0** |
| **CFQS pass %** | — | **100** |
| Reasoning changed | No | **No** |

### Smoke / CIO-25

| Suite | Pass % | Mean | HQS | CQS | CFQS |
|-------|-------:|-----:|----:|----:|-----:|
| smoke (20) | 100 | 87.92 | 97.32 | 96.40 | 100.0 |
| cio_frozen_25 | 100 | 87.58 | 95.20 | 95.26 | 100.0 |

## Exit gate

| Gate | Status |
|------|--------|
| Deterministic confidence | ✓ |
| Replay / temporal integrity | ✓ |
| Missing evidence / conflict / disagreement lower confidence | ✓ |
| Fixtures never increase confidence | ✓ |
| Explanations generated (numeric + reason) | ✓ |
| No reasoning / framework / communication regression | ✓ |
| LangSmith `confidence_calibration` | ✓ |
| CFQS generated | ✓ 100.0 |
| HQS / CQS maintained | ✓ |
| CIO maintained | ✓ 100% |

## Phase 4 certification posture

Judgment stack complete:

```text
IEW → IHG → IHE → ICR → ICC → Reasoning → ICE
```

Recommend full certification programme, then freeze IEW/IHG/IHE/ICR/ICC as **v1.0.0** and begin Phase 5 (investment decisions over time) — not more judgment layers.
