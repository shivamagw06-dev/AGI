# AGI ICR Evaluation — Phase 4 Sprint 4.4

```text
COMPANY: AGI
SPRINT: Phase 4 · Sprint 4.4 Institutional Committee Reasoning
ICR: institutional-committee-reasoning-v1.0.0
CQS: cqs-v1.0.0
DATE: 2026-07-28
```

## Method

- Soft-wire ICR after frozen IHE in Ask pipeline + IEL soft probe.
- Run `institutional_1000` + `cio_frozen_25` (soft).
- Compare IEL / CIO / HQS to IHE baseline; introduce CQS independently.
- Bull / Base / Bear treated as **roles** (upside / balance / downside), not fixed templates.
- Probabilities = relative support; must sum to 100%.

## Results

| Metric | Frozen v3.5 | IHE soft | ICR soft |
|--------|------------:|---------:|---------:|
| IEL 1000 pass % | 99.9 | 99.9 | **99.9** |
| IEL mean | 90.24 | 90.05 | **90.05** |
| CIO-25 pass % | 100 | 100 | **100** |
| HQS mean | — | 95.85 | **95.85** |
| HQS pass % | — | 100 | **100** |
| **CQS mean** | — | — | **95.89** |
| **CQS pass %** | — | — | **100** |
| Reasoning changed | No | No | **No** |

### CQS components (IEL 1000)

| Component | Mean |
|-----------|-----:|
| Bull completeness | 95.02 |
| Base realism | 99.10 |
| Bear completeness | 75.01 |
| Probability calibration | 100.00 |
| Assumption quality | 99.10 |
| Catalyst quality | 99.10 |
| Risk quality | 99.10 |
| Invalidation quality | 99.10 |
| Committee explainability | 99.55 |

Bear completeness is intentionally lower: ICR does **not** force a Bear role when evidence only supports Base (and optionally Bull). Partial credit is awarded for correct non-fabrication.

## Smoke / CIO-25

| Suite | Pass % | Mean | Mean HQS | Mean CQS |
|-------|-------:|-----:|---------:|---------:|
| smoke (20) | 100 | 87.92 | 97.32 | 96.40 |
| cio_frozen_25 | 100 | 87.58 | 95.20 | 95.26 |

## Exit gate

| Gate | Status |
|------|--------|
| Deterministic committee construction | ✓ |
| Replay integrity / frozen upstream | ✓ |
| Probabilities sum to 100% | ✓ |
| Contradictory evidence retained | ✓ |
| Assumptions / catalysts / risks / invalidation recorded | ✓ |
| Preferred case explained | ✓ |
| No reasoning / framework / communication regression | ✓ |
| LangSmith `committee_deliberation` (+ `.case`) | ✓ |
| CQS generated (independent of CIO / HQS) | ✓ |
| HQS maintained | ✓ 95.85 |
| CIO maintained | ✓ 100% |
| Analytical depth (committee report before reasoning) | ✓ |

## Next

Sprint **4.5 Confidence Calibration** — confidence as an emergent property of committee deliberation.
